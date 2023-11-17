"""Main app definition"""
# pylint: disable=broad-exception-caught, exec-used
import logging
import sys
import json
from datetime import datetime as pydate
from datetime import timedelta
from click import secho
from elasticsearch8.helpers import bulk, BulkIndexError
from es_client.helpers.utils import prune_nones
from es_timeslicer.helpers.client import get_args, get_client
from es_timeslicer.helpers import utils
from es_timeslicer.exceptions import ConfigurationException, FatalException, MissingArgument

ARGS = [
    'read_index', 'write_index', 'pipeline', 'field', 'start_time', 'end_time', 'increment',
    'agg_function', 'query_file', 'trace'
]

def load_function(filename, global_vars=None, local_vars=None):
    """Assume that filename contains only 1 function"""
    if not global_vars:
        global_vars = {}
    if not local_vars:
        local_vars = {}
    with open(filename, 'r', encoding='utf8') as f:
        file_contents = f.read()
        exec(file_contents, global_vars, local_vars)
        return next(f for f in local_vars.values() if callable(f))

class TimeSlicer:
    """It's the main class"""
    def __init__(self, client_params, params):
        self.logger = logging.getLogger(__name__)
        self.logger.debug('Initializing TimeSlicer class object')
        try:
            client_args, other_args = get_args(client_params)
            self.client = get_client(configdict={
                'elasticsearch': {
                    'client': prune_nones(client_args.asdict()),
                    'other_settings': prune_nones(other_args.asdict())
                }
            })
        except Exception as exc:
            self.logger.critical('Unable to establish client connection: %s', exc)
            raise FatalException from exc

        for key in ARGS:
            if not key in params:
                msg = f'"{key}" not in parameters'
                self.logger.critical(msg)
                raise MissingArgument(msg)
        self.params = params
        self.end_dt = self.verify_date(params['start_time'])
        self.range_start_dt = self.verify_date(params['end_time'])
        self.trace = params['trace']

    def bulk_generator(self, data):
        """Python generator to feed the bulk input"""
        for entry in data:
            yield entry

    def get_query(self):
        """Get the raw query from the query_file"""
        try:
            query = utils.read_queryfile(self.params['query_file'])
        except Exception as exc:
            self.logger.critical('Error reading from query_file: %s', exc)
            raise FatalException from exc
        return query

    def get_range_filter(self, begin, end):
        """Set the range filter in the query"""
        return {
            "range": {
                self.params['field']: {
                    "gte": begin,
                    "lt": end
                }
            }
        }

    def get_rangevals(self):
        """Add increment to self.range_start_dt to set the rangevals"""
        begin = self.range_start_dt.isoformat()
        delta = timedelta(minutes=self.params['increment'])
        end = (self.range_start_dt + delta).isoformat()
        if pydate.fromisoformat(end) > self.end_dt:
            end = self.end_dt.isoformat()
        return begin, end

    def loop_query(self):
        """Loop the query"""
        request = self.get_query()
        self.logger.debug('Loading agg function from file.')
        try:
            gvars = {'__builtins__': {'float': float}}
            lvars = {}
            agg_function = load_function(
                self.params['agg_function'], global_vars=gvars, local_vars=lvars)
        except Exception as exc:
            self.logger.error('Unable to load agg_function: %s', self.params['agg_function'])
            self.logger.critical('Error: %s', exc)
            raise FatalException from exc
        while self.range_start_dt < self.end_dt:
            begin, end = self.get_rangevals()
            self.logger.debug('Timeslice: BEGIN: %s, END: %s', begin, end)
            range_filter = self.get_range_filter(begin, end)
            request = self.update_request(request, range_filter)
            if self.trace:
                msg = f'TRACE: REQUEST: \n{json.dumps(request, indent=2)}'
                self.logger.debug(msg)
            reqkeys = list(request.keys())
            agg = None
            if 'aggs' in reqkeys:
                agg = request['aggs']
            elif 'aggregations' in reqkeys:
                agg = request['aggregations']
            result = self.client.search(
                index=self.params['read_index'],
                aggs=agg, query=request['query'],
                size=request['size']
            )
            if self.trace:
                msg = f'TRACE: RESULT: \n{json.dumps(dict(result), indent=2)}'
                self.logger.debug(msg)
            try:
                documents = agg_function(
                                result, self.params['write_index'], self.params['pipeline'])
            except Exception as exc:
                msg = f'Error executing function "{self.params["agg_function"]}": Error: {exc}'
                self.logger.critical(msg)
                raise FatalException from exc
            if documents:
                if self.params['dry_run']:
                    secho('DRY-RUN: DOCUMENT PREVIEW:', bold=True)
                    secho(f'{json.dumps(documents, indent=2)}', bold=True)
                    secho('DRY-RUN: COMPLETED. Exiting.', bold=True)
                    sys.exit(0)
                else:
                    self.logger.debug('Bulk-writing documents to %s', self.params['write_index'])
                    try:
                        bulk(
                            self.client,
                            self.bulk_generator(documents),
                            max_retries=10,
                            initial_backoff=1
                        )
                    except BulkIndexError as bie:
                        msg = f'Bulk indexing encountered one or more errors: \n{bie.errors}'
                        self.logger.error(msg)
                    except Exception as exc:
                        self.logger.error('Exception encountered during bulk write to ES: %s', exc)
                        raise FatalException from exc
            else:
                self.logger.debug('No documents found in this time slice. Continuing...')
            # After successful iteration, update range_start_dt:
            self.range_start_dt = pydate.fromisoformat(end)

    def update_request(self, request, range_filter):
        """Return an updated request that has the desired date range filter"""
        if not 'bool' in request['query']:
            request['query']['bool'] = {'filter': [range_filter]}
        elif not 'filter' in request['query']['bool']:
            request['query']['bool']['filter'] = [range_filter]
        elif 'filter' in request['query']['bool']:
            if isinstance(request['query']['bool']['filter'], list):
                found = False
                for entry in request['query']['bool']['filter']:
                    if 'range' in entry:
                        if self.params['field'] in list(entry['range'].keys()):
                            # We found it, now replace it.
                            found = True
                            request['query']['bool']['filter'].remove(entry)
                            request['query']['bool']['filter'].append(range_filter)
                if not found:
                    # It was not found in the current list of filters, so append it
                    request['query']['bool']['filter'].append(range_filter)
            else: # This is a single filter, which may need to become an array
                if 'range' in request['query']['bool']['filter']:
                    if self.params['field'] in list(entry['range'].keys()):
                        # Update as an array this time
                        request['query']['bool']['filter'] = [range_filter]
                else:
                    # We had a single filter, which is now an array including the range filter
                    replacement = [request['query']['bool']['filter'], range_filter]
                    request['query']['bool']['filter'] = replacement
        return request

    def verify_date(self, date):
        """Verify that the date is valid ISO8601"""
        value = ''
        try:
            value = pydate.fromisoformat(date)
        except ValueError as exc:
            self.logger.critical('"%s" is not valid ISO8601. Exiting...', date)
            raise ConfigurationException from exc
        return value

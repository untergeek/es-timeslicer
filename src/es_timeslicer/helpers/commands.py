"""Sub-commands for Click CLI"""
import logging
import click
from es_client.helpers import utils as escl
from es_timeslicer.defaults import FILEPATH_OVERRIDE, EPILOG, get_context_settings
from es_timeslicer.exceptions import FatalException
from es_timeslicer.helpers.client import get_args, get_client
from es_timeslicer.helpers.utils import cli_opts, is_docker
from es_timeslicer.main import TimeSlicer

LOGGER = logging.getLogger(__name__)

ONOFF = {'on': 'show-', 'off': 'hide-'}
click_opt_wrap = escl.option_wrapper()

def override_filepath():
    """Override the default filepath if we're running Docker"""
    if is_docker():
        return {'default': FILEPATH_OVERRIDE}
    return {}

# pylint: disable=unused-argument
@click.command(context_settings=get_context_settings(), epilog=EPILOG)
@click_opt_wrap(*cli_opts('read_index'))
@click_opt_wrap(*cli_opts('write_index'))
@click_opt_wrap(*cli_opts('pipeline'))
@click_opt_wrap(*cli_opts('field'))
@click_opt_wrap(*cli_opts('start_time'))
@click_opt_wrap(*cli_opts('end_time'))
@click_opt_wrap(*cli_opts('increment')) # in minutes
@click_opt_wrap(*cli_opts('agg_function'))
@click_opt_wrap(*cli_opts('dry_run'))
@click_opt_wrap(*cli_opts('trace'))
@click.argument('query_file', type=str, nargs=1)
@click.pass_context
def query(
    ctx, read_index, write_index, pipeline, field, start_time, end_time, increment, agg_function,
    dry_run, trace, query_file):
    """
    Repeatedly execute the query in QUERY_FILE using the defined parameters.

    $ es-timeslicer query [OPTIONS] QUERY_FILE
    """
    LOGGER.debug('Entering function "query"')
    tslicer = TimeSlicer(ctx.parent.params, ctx.params)
    try:
        tslicer.loop_query()
    except Exception as exc:
        LOGGER.critical('Error encountered during execution: %s', exc)
        LOGGER.critical('Unable to continue. Exiting.')
        raise FatalException from exc

@click.command(context_settings=get_context_settings(), epilog=EPILOG)
@click.argument('search_pattern', type=str, nargs=1)
@click.pass_context
def show_indices(ctx, search_pattern):
    """
    Show indices on the console matching SEARCH_PATTERN

    $ es-timeslicer show_indices SEARCH_PATTERN

    This is included as a way to ensure you are seeing the indices you expect.
    """
    client_args, other_args = get_args(ctx.parent.params)
    try:
        client = get_client(configdict={
            'elasticsearch': {
                'client': escl.prune_nones(client_args.asdict()),
                'other_settings': escl.prune_nones(other_args.asdict())
            }
        })
    except Exception as exc:
        LOGGER.critical('Exception encountered: %s', exc)
        raise FatalException from exc
    cat = client.cat.indices(index=search_pattern, h='index', format='json')
    indices = []
    for item in cat:
        indices.append(item['index'])
    indices.sort()
    # Output
    ## Search Pattern
    click.secho('\nSearch Pattern', nl=False, overline=True, underline=True, bold=True)
    click.secho(f': {search_pattern}', bold=True)
    ## Indices Found
    if len(indices) == 1:
        click.secho('\nIndex Found', nl=False, overline=True, underline=True, bold=True)
        click.secho(f': {indices[0]}', bold=True)
    else:
        click.secho(f'\n{len(indices)} ', overline=True, underline=True, bold=True, nl=False)
        click.secho('Indices Found', overline=True, underline=True, bold=True, nl=False)
        click.secho(': ')
        for idx in indices:
            click.secho(idx)

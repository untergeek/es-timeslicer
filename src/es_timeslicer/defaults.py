"""Default values and constants"""
from shutil import get_terminal_size
import click
from six import string_types
from voluptuous import All, Any, Coerce, Optional, Schema

# pylint: disable=E1120

# This value is hard-coded in the Dockerfile, so don't change it

FILEPATH_OVERRIDE = '/fileoutput'

EPILOG = 'Learn more at https://github.com/untergeek/es-timeslicer'

HELP_OPTIONS = {'help_option_names': ['-h', '--help']}

CLI_OPTIONS = {
    'loglevel': {
        'help': 'Log level',
        "type": click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    },
    'logfile': {'help': 'Log file', 'type': str},
    'logformat': {
        'help': 'Log output format',
        "type": click.Choice(['default', 'ecs'])
    },
    'show_hidden': {'help': 'Show all options', 'is_flag': True, 'default': False},
    'read_index': {'help': 'The index to query', 'required': True},
    'write_index': {'help': 'The target index', 'required': True},
    'pipeline': {
        'help': 'Send to the named pipeline', 'type': str, 'required': False, 'default': None},
    'field': {'help': 'The timestamp field name', 'default': '@timestamp', 'show_default': True},
    'start_time': {
        'help': 'The ISO8601 formatted date closest to now (newest) of your date range',
        'required': True
    },
    'end_time': {
        'help': 'The ISO8601 formatted date farthest from now (oldest) of your date range',
        'required': True
    },
    'increment': {
        'help': 'The time slice increment in minutes',
        'type': int,
        'default': 1,
        'show_default': True
    },
    'agg_function': {
        'help': 'File with a single Python function that prepares and formats documents',
        'type': str,
        'required': True
    },
    'dry_run': {
        'help': 'Do a dry-run, and output a few results to the console as a test',
        'is_flag': True,
        'default': False
    },
    'trace': {
        'help': 'Enable trace (super-debug) logging of requests and responses. Not for production!',
        'is_flag': True,
        'default': False
    },
}

def click_options():
    """Return the max version"""
    return CLI_OPTIONS

# Configuration file: logging
def config_logging():
    """
    Logging schema with defaults:

    .. code-block:: yaml

        logging:
          loglevel: INFO
          logfile: None
          logformat: default
          blacklist: ['elastic_transport', 'urllib3']

    :returns: A valid :py:class:`~.voluptuous.schema_builder.Schema` of all acceptable values with
        the default values set.
    :rtype: :py:class:`~.voluptuous.schema_builder.Schema`
    """
    return Schema(
        {
            Optional('loglevel', default='INFO'):
                Any(None, 'NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
                    All(Coerce(int), Any(0, 10, 20, 30, 40, 50))
                    ),
            Optional('logfile', default=None): Any(None, *string_types),
            Optional('logformat', default='default'):
                Any(None, All(Any(*string_types), Any('default', 'ecs'))),
            Optional('blacklist', default=['elastic_transport', 'urllib3']): Any(None, list),
        }
    )

def get_context_settings():
    """Return Click context settings dictionary"""
    return {**get_width(), **HELP_OPTIONS}

def get_width():
    """Determine terminal width"""
    return {"max_content_width": get_terminal_size()[0]}

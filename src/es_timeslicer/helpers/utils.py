"""Utility helper functions"""

import logging
from json import load
from pathlib import Path
import click
from es_timeslicer.defaults import click_options
from es_timeslicer.exceptions import ConfigurationException, FatalException

LOGGER = logging.getLogger(__name__)
NOPE = 'DONOTUSE'

def cli_opts(value, onoff=None, override=None):
    """
    In order to make building a Click interface more cleanly, this function returns all Click
    option settings indicated by ``value``, both forming the lone argument (e.g. ``--option``),
    and all key word arguments as a dict.

    The single arg is rendered as ``f'--{value}'``. Likewise, ``value`` is the key to extract
    all keyword args from the supplied dictionary.
    The facilities to override default values and show hidden values is added here.
    For default value overriding, the NOPE constant is used as None and False are valid default
    values
    """
    if override is None:
        override = {}
    argval = f'--{value}'
    if isinstance(onoff, dict):
        try:
            argval = f'--{onoff["on"]}{value}/--{onoff["off"]}{value}'
        except KeyError as exc:
            raise ConfigurationException from exc
    # return (argval,), override_hidden(retval, show=show)
    return (argval,), override_settings(click_options()[value], override)

def is_docker():
    """Check if we're running in a docker container"""
    cgroup = Path('/proc/self/cgroup')
    return Path('/.dockerenv').is_file() or (
        cgroup.is_file() and 'docker' in cgroup.read_text(encoding='utf-8'))

def option_wrapper():
    """Return the click decorator passthrough function"""
    return passthrough(click.option)

def override_settings(data, new_data):
    """Override keys in data with values matching in new_data"""
    if not isinstance(new_data, dict):
        raise ConfigurationException('new_data must be of type dict')
    for key in list(new_data.keys()):
        if key in data:
            data[key] = new_data[key]
    return data

def passthrough(func):
    """Wrapper to make it easy to store click configuration elsewhere"""
    return lambda a, k: func(*a, **k)

def read_queryfile(filename):
    """Read a JSON file and return its contents as a dict"""
    retval = {}
    try:
        with open(filename, 'r', encoding='utf8') as filehandle:
            retval = load(filehandle)
    except Exception as exc:
        LOGGER.critical('Unable to read query file: %s', exc)
        raise FatalException from exc
    if not retval:
        msg = 'Empty query file. Exiting.'
        LOGGER.critical(msg)
        raise ConfigurationException(msg)
    return retval

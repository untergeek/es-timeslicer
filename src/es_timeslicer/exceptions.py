"""es-timeslicer Exceptions"""
### Parent exception
class TimeSlicerException(Exception):
    """
    Base class for all exceptions raised by the tool which are not Elasticsearch
    exceptions.
    """
###

class ClientException(TimeSlicerException):
    """
    Exception raised when the Elasticsearch client and/or connection is the source of the problem.
    """

class ConfigurationException(TimeSlicerException):
    """
    Exception raised when there is a configuration error
    """

class MissingArgument(ConfigurationException):
    """
    Exception raised when a required argument or parameter is missing
    """

class ResultNotExpected(ClientException):
    """
    Exception raised when return value from Elasticsearch API call is not or does not contain the
    expected result.
    """

class TimeoutException(TimeSlicerException):
    """
    Exception raised when a task has failed because the allotted time ran out
    """

class ValueMismatch(ConfigurationException):
    """
    Exception raised when a received value does not match what was expected.
    """

class FatalException(TimeSlicerException):
    """
    Exception raised when the program should be halted.
    """

import datetime
from dateutil import parser


class DateTimeValueError(ValueError):
    pass


def ensure_datetime(value):
    """
    Ensures that the provided value is a `obj:datetime.datetime` instance
    by either converting a `obj:str` to a `obj:datetime.datetime` instance
    or a `obj:datetime.date` instance to a `obj:datetime.datetime` instance.
    If the value cannot be safely converted to a `obj:datetime.datetime`
    instance, a ValueError will be raised.

    Parameters:
    -----------
    value: :obj:`datetime.datetime`, :obj:`datetime.date` or :obj:`str`
        The value that should be converted to a :obj:`datetime.datetime`
        instance.
    """
    if type(value) is datetime.datetime:
        return value
    elif type(value) is datetime.date:
        return datetime.datetime.combine(value, datetime.datetime.min.time())
    elif isinstance(value, str):
        try:
            return parser.parse(value)
        except ValueError as e:
            raise DateTimeValueError(
                "The provided value cannot be converted to a "
                "datetime.datetime instance."
            ) from e
    else:
        raise DateTimeValueError(
            "Invalid value %s supplied - cannot convert to datetime." % value)

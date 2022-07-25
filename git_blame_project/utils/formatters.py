import pathlib


def path_formatter():
    def _formatter(value):
        if not isinstance(value, pathlib.Path):
            return pathlib.Path(value)
        return value
    return _formatter


CONJUNCTIONS = ['or', 'and']


def humanize_list(value, callback=str, conjunction='and', oxford_comma=True,
        strict_none=False):
    """
    Returns a human readable string for the provided iterable.
    """
    if conjunction.lower() not in CONJUNCTIONS:
        raise TypeError(
            "Expected values `or` or `and` for conjunction, but received "
            f"{conjunction}."
        )
    elif value is None:
        if strict_none:
            raise TypeError("The provided value cannot be null.")
        return value

    value = list(value)
    num = len(value)
    if num == 0:
        return ""
    elif num == 1:
        return callback(value[0])
    if conjunction:
        s = ", ".join(map(callback, value[:num - 1]))
        if len(value) >= 3 and oxford_comma is True:
            s += ","
        return "%s %s %s" % (s, conjunction.lower(), callback(value[num - 1]))
    return ", ".join(map(callback, value[:num]))


def humanize_dict(value, formatter=None, delimeter=" "):
    """
    Returns a human readable string for the provided mapping.
    """
    if not isinstance(value, dict):
        raise TypeError(
            f"The provided value must be of type {dict}, not {type(value)}.")
    parts = []
    for k, v in value.items():
        if formatter is not None:
            v = formatter(v)
        parts.append(f"{k}={v}")
    return delimeter.join(parts)

def humanize_list(value, callback=str, conjunction='and', oxford_comma=True):
    """
    Turns an interable list into a human readable string.
    """
    num = len(value)
    if num == 0:
        return ""
    elif num == 1:
        return callback(value[0])
    if conjunction:
        s = ", ".join(map(callback, value[:num - 1]))
        if len(value) >= 3 and oxford_comma is True:
            s += ","
        return "%s %s %s" % (s, conjunction, callback(value[num - 1]))
    return ", ".join(map(callback, value[:num]))


def iterable_from_args(*args, cast=list, strict=True):
    if len(args) == 0:
        if strict:
            raise ValueError("At least one value must be provided.")
        return []
    elif len(args) == 1:
        if hasattr(args[0], '__iter__') and not isinstance(args[0], str):
            return cast(args[0])
        return cast([args[0]])
    else:
        return cast([args[:]])

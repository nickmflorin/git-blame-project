import importlib


class empty:
    """
    This class is used to represent no data being provided for a given input
    or output value.
    It is required because `None` may be a valid input or output value.
    """
    @classmethod
    def default(cls, value, default):
        if value is empty:
            return default
        return value


class LazyFn:
    def __init__(self, func, *args, **kwargs):
        self._func = func
        if len(args) == 0 and 'args' in kwargs:
            self._args = list(kwargs.pop('args'))
        else:
            self._args = list(args)
        if 'kwargs' in kwargs:
            self._kwargs = kwargs.pop('kwargs')
        else:
            self._kwargs = kwargs

    def __call__(self):
        arguments = []
        for argument in self._args:
            if is_function(argument):
                arguments.append(argument())
            else:
                arguments.append(argument)
        return self._func(*arguments, **self._kwargs)


def klass(instance_or_cls):
    if not isinstance(instance_or_cls, type):
        return instance_or_cls.__class__
    return instance_or_cls


def obj_name(obj):
    if hasattr(obj, '__class__'):
        return obj.__class__.__name__
    elif hasattr(obj, '__name__'):
        return obj.__name__
    elif not isinstance(obj, str):
        raise TypeError(
            f"Expected a class, a class instance, a function or a string, "
            f"but received {type(obj)}."
        )
    return obj


def is_function(func):
    return hasattr(func, '__call__') and type(func) is not type


def is_iterable(value):
    return not isinstance(value, str) and hasattr(value, '__iter__')


def cjoin(*args, delimiter=" ", invalids=empty, formatter=None):
    string_args = []
    invalids = ensure_iterable(empty.default(invalids, [None]))
    for a in args:
        if a not in invalids:
            if formatter is not None:
                string_args.append(formatter(str(a)))
            else:
                string_args.append(str(a))
    if len(string_args) == 0:
        return ""
    return delimiter.join(string_args)


def humanize_list(value, callback=str, conjunction='and', oxford_comma=True):
    """
    Turns an interable list into a human readable string.
    """
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
        return "%s %s %s" % (s, conjunction, callback(value[num - 1]))
    return ", ".join(map(callback, value[:num]))


def humanize_dict(value, formatter=None, delimeter=" "):
    if not isinstance(value, dict):
        raise TypeError(
            f"The provided value must be of type {dict}, not {type(value)}.")
    parts = []
    for k, v in value.items():
        if formatter is not None:
            v = formatter(v)
        parts.append(f"{k}={v}")
    return delimeter.join(parts)


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
        return cast(args[:])


def pluck_first_kwarg(*args, **kwargs):
    for a in args:
        if a in kwargs:
            return kwargs[a]
    return None


def ensure_iterable(value, strict=False, cast=list, cast_none=True):
    """
    Ensures that the provided value is an iterable that can be indexed
    numerically.
    """
    if value is None:
        if cast_none:
            return cast()
        return None
    # A str instance has an `__iter__` method.
    if isinstance(value, str):
        return [value]
    elif hasattr(value, '__iter__') and not isinstance(value, type):
        # We have to cast the value instead of just returning it because a
        # instance of set() has the `__iter__` method but is not indexable.
        return cast(value)
    elif strict:
        raise ValueError("Value %s is not an iterable." % value)
    return cast([value])


def import_at_module_path(module_path):
    """
    Imports the class or function at the provided module path.
    """
    module_name = ".".join(module_path.split(".")[:-1])
    class_name = module_path.split(".")[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

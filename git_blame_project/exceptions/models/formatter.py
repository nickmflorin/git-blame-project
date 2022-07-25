from git_blame_project import utils


class Formatter:
    """
    A class that wraps a formatting function such that additional context can
    be provided to the underlying formatting function.

    Usage:
    -----
    Generally, formatting functions are defined as functions that take a value
    as its only argument and return the formatted value:

    >>> def string_formatter(value):
    >>>     return f"{value}

    Throughout this package, formatting functions are commonly defined inline
    as configuration options to classes that leverage the
    :obj:`FormattableModelMixin` mixin:

    >>> class MyConfigurableObj(Configurable):
    >>>     configuration = [Config(param='foo', formatter=[string_formatter])]

    However, it is also commonly the case that the formatting functions need
    additional context:

    >>> def string_suffix_formatter(value, instance):
    >>>     if getattr(instance, 'suffix', None) is not None:
    >>>         return f"{value}{instance.suffix}
    >>>     return f"{value}"

    In this case, we can wrap the :obj:`string_formatter` method in this
    :obj:`Formatter` class such that the additional arguments can be provided
    to the :obj:`Formatter` instance and passed through to the underlying
    formatting function:

    >>> class MyConfigurableObj(Configurable):
    >>>     configuration = [
    >>>         Config(
    >>>             param='foo',
    >>>             formatter=Formatter(lambda instance: [
    >>>                 string_formatter,
    >>>                 functools.partial(
    >>>                     string_suffix_formatter, instance=instance)
    >>>             ]
    >>>         )
    >>> ]

    Now, the formatting function is called with the additional context and
    the context is passed through to the underlying formatting functions that
    require it:

    >>> o = MyConfigurableObj(suffix=".")
    >>> o.configuration[0].formattter("bar", instance)
    >>> "bar."

    Parameters:
    ----------
    func: :obj:`lambda`
        The underlying format function that takes a value as its only argument
        and returns a formatted value.
    """
    def __init__(self, func):
        self._func = func

    def __call__(self, value, *args, **kwargs):
        funcs = utils.ensure_iterable(self._func(*args, **kwargs))
        for func in funcs:
            value = func(value)
        return value

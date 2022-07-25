from git_blame_project import utils


__all__ = ('FormattableModelMixin', )


class FormattableModelMixin:
    """
    A mixin that allows a class to be configured with a means of formatting
    values and behaviors that allow those values to be formatted based on the
    configuration.

    Parameters:
    ----------
    formatter: :obj:`lambda` or :obj:`Formatter` or :obj:`list` or :obj:`tuple`
        Either a single formatter or an iterable of formatters.  Each formatter
        can be a simple single argument function or a :obj:`Formatter` instance.

        If provided as a simple function, the function should take the
        unformatted value as its only argument and return the formatted value.
    """
    def __init__(self, **kwargs):
        self._formatter = kwargs.pop('formatter', None)
        self._format_null_values = kwargs.pop('format_null_values', False)

    @property
    def format_null_values(self):
        """
        Returns whether or not null values should be formatted.  If False,
        the formatters that this class is configured with will not be applied
        to a value if that value is None.
        """
        return self._format_null_values

    @property
    def formatter(self):
        return utils.ensure_iterable(self._formatter)

    def format(self, value, *args, **kwargs):
        """
        Formats the provided value based on the formatters that the class
        is configured with.
        """
        from .formatter import Formatter

        if value is not None or self.format_null_values is True:
            for fmt in self.formatter:
                if isinstance(fmt, Formatter):
                    value = fmt(value, *args, **kwargs)
                else:
                    value = fmt(value)
        return value

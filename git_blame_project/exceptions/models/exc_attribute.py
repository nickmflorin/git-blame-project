from .mixins import FormattableModelMixin


class ExceptionAttribute(FormattableModelMixin):
    """
    Represents an attribute of the :obj:`AbstractException` class - that can
    be provided on initialization or defined statically on the class - along
    with additional information that define how the attribute value is accessed,
    defaulted and formatted.
    """
    def __init__(self, name, **kwargs):
        self._name = name
        self._accessor = kwargs.pop('accessor', None)
        FormattableModelMixin.__init__(self, **kwargs)
        self._default = kwargs.pop('default', None)

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def accessor(self):
        return self._accessor or self._name

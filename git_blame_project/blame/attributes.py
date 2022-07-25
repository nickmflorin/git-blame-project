from abc import ABC, abstractmethod

from git_blame_project import exceptions, utils

from .exceptions import BlameLineAttributeParserError


class LineAttribute(ABC):
    """
    Abstract class that represents an attribute that is defined on the
    :obj:`BlameLine`.
    """
    should_save = True
    attr = None

    def __init__(self, name, title):
        self._title = title
        self._name = name

    @property
    def title(self):
        return self._title

    @property
    def name(self):
        return self._name

    @abstractmethod
    def parse(self, *args, **kwargs):
        pass

    def save(self, line, value):
        if self.should_save:
            setattr(line, self.name, value)


class DependentAttribute(LineAttribute):
    """
    Represents an attribute of a :obj:`BlameLine` that depends on the set of
    :obj:`ParsedAttribute`(s) whose values are directly determined from the
    blamed string.  The attributes defined by :obj:`DependentAttribute` are
    set on the :obj:`BlameLine` after all of the attributes defined by
    :obj:`ParsedAttribute` are set.
    """
    def __init__(self, name, title, **kwargs):
        super().__init__(name, title)
        if not hasattr(self, 'parse') and 'parse' not in kwargs:
            raise exceptions.ImproperUsageError(
                instance=self,
                message=(
                    "The `parse` method must either be defined statically on "
                    "the {cls_name} class or be provided on initialization."
                )
            )
        self._parse = kwargs.get('parse', None)

    def parse(self, parsed_attributes):
        if self._parse is None:
            if type(self) is DependentAttribute:
                # We should not get to this point, but it is cleaner to raise
                # an exception here instead of making an assertion.
                raise TypeError(
                    "The `parse` method should have been provided on "
                    "initialization."
                )
            else:
                raise TypeError(
                    f"The `parse` method of the base {DependentAttribute} "
                    f"class should not be called from {self.__class__}."
                )
        return self._parse(parsed_attributes)


class ExistingLineAttribute(DependentAttribute):
    """
    Represents an existing attribute of a :obj:`BlameLine` that should be
    treated as an attribute such that it is included in tabular data that is
    outputted for the given :obj:`BlameLine`.

    Unlike other extensions of :obj:`LineAttribute`, whether or not attributes
    defined with :obj:`ExistingLineAttribute` will be set on the
    :obj:`BlameLine` depends on whether or not the `attr` is provided to the
    :obj:`ExistingLineAttribute` on initialization.

    Parameters:
    ----------
    formatter: :obj:`lambda` (optional)
        A callback that returns the formatted value of the attribute that
        should be set on the :obj:`BlameLine`.

        Note: If the `formatter` parameter is provided, the `attr` value must
        also be provided - otherwise the formatted value will override the
        original value on the :obj:`BlameLine`.

        Default: None

    attr: :obj:`str` (optional)
        The name of the attribute on the :obj:`BlameLine` instance that the
        value is read from in the case that the original value differs from
        the value returned by the `parse` method - which usually happens if
        a `formatter` is provided.

        In the case that a `formatter` is provided, the formatted value will
        usually differ from the original value on the :obj:`LineBlame` instance.
        In this case, we do not want to (and usually cannot if the original
        attribute was defined with an @property) set the formatted value on
        the :obj:`BlameLine` using the same attribute name that the original
        value is associated with - we need to save the formatted value with
        a different attribute name.

        In this case, we define the `attr` parameter - which is used to obtain
        the original attribute value on the :obj:`BlameLine` instance - and
        the `name` parameter is used to set the value on the :obj:`BlameLine`
        instance.

        Note: When the `attr` parameter is not provided, the value returned
        from the `parse` method is not actually set on the :obj:`BlameLine`
        instance - because it already exists.

        Default: None
    """
    def __init__(self, name, title, formatter=None, attr=None):
        super().__init__(name, title)
        self._formatter = formatter
        self._attr = attr
        # If the formatter is provided and the attr is not provided, the
        # formatted attribute value - which will usually differ from the
        # original attribute value - will be set on the instance.
        if self._formatter is not None and self._attr is None:
            raise exceptions.ImproperUsageError(
                instance=self,
                message=(
                    "If the `formatter` parameter is provided, the `attr` must "
                    "also be provided such that the formatted value does not "
                    "overwrite the original value on the instance."
                )
            )

    @property
    def should_save(self):
        # Whether or not the attribute should be set on the line instance is
        # completely dependent on whether or not the `attr` parameter is
        # provided on initialization.
        return self._attr is not None

    @property
    def attr(self):
        return self._attr or self.name

    def parse(self, line):
        assert hasattr(line, self.attr), \
            f"The line does not have an existing attribute `{self.attr}`."
        v = getattr(line, self.attr)
        if self._formatter is not None:
            return self._formatter(v)
        return v


class ParsedAttribute(LineAttribute):
    """
    Represents an attribute of a :obj:`BlameLine` that is directly determined
    from the blamed string.
    """
    def __init__(self, name, regex_index, title, critical=True):
        super().__init__(name, title)
        self._regex_index = regex_index
        self._critical = critical

    def fail(self, data, context, **kwargs):
        raise BlameLineAttributeParserError(
            data=data,
            attr=self.name,
            critical=self._critical,
            context=context,
            **kwargs
        )

    def get_raw_value(self, groups):
        if hasattr(self._regex_index, '__iter__'):
            return [groups[i].strip() for i in self._regex_index]
        return groups[self._regex_index].strip()

    # pylint: disable=inconsistent-return-statements
    def parse(self, data, groups, context):
        try:
            return self.get_raw_value(groups)
        except IndexError:
            self.fail(data, context)


class DateTimeParsedAttribute(ParsedAttribute):
    def get_raw_value(self, groups):
        parts = super().get_raw_value(groups)
        date_string = "-".join(parts[:3])
        time_string = ":".join(parts[3:])
        return f"{date_string} {time_string}"

    # pylint: disable=inconsistent-return-statements
    def parse(self, data, groups, context):
        value = super().parse(data, groups, context)
        try:
            return utils.ensure_datetime(value)
        except utils.DateTimeValueError:
            self.fail(data, context, value=value)


class IntegerParsedAttribute(ParsedAttribute):
    # pylint: disable=inconsistent-return-statements
    def parse(self, data, groups, context):
        value = super().parse(data, groups, context)
        try:
            return int(value)
        except ValueError:
            self.fail(data, context, value=value)

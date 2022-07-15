from abc import ABC, abstractmethod

from git_blame_project.utils import ensure_datetime, DateTimeValueError
from .exceptions import BlameLineAttributeParserError


class LineAttribute(ABC):
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


class DependentAttribute(LineAttribute):
    def __init__(self, name, title, **kwargs):
        super().__init__(name, title)
        if not hasattr(self, 'parse') and 'parse' not in kwargs:
            raise TypeError(
                "A dependent attribute must either define a `parse` method "
                "statically on the class or be provided with the method "
                "on initialization."
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


class ParsedAttribute(LineAttribute):
    def __init__(self, name, regex_index, title, critical=True):
        super().__init__(name, title)
        self._regex_index = regex_index
        self._critical = critical

    def fail(self, data, context, **kwargs):
        raise BlameLineAttributeParserError(
            data=data,
            attr=self._attr,
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
            return ensure_datetime(value)
        except DateTimeValueError:
            self.fail(data, context)


class IntegerParsedAttribute(ParsedAttribute):
    # pylint: disable=inconsistent-return-statements
    def parse(self, data, groups, context):
        value = super().parse(data, groups, context)
        try:
            return int(value)
        except ValueError:
            self.fail(data, context, value=value)

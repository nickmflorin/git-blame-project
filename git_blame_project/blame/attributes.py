from git_blame_project.utils import ensure_datetime, DateTimeValueError
from .exceptions import BlameLineAttributeParserError


class ParsedAttribute:
    def __init__(self, name, regex_index, title, critical=True):
        self._name = name
        self._title = title
        self._regex_index = regex_index
        self._critical = critical

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return self._title

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

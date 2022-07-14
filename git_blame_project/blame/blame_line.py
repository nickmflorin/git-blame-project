import re

import click

from .attributes import (
    ParsedAttribute, IntegerParsedAttribute, DateTimeParsedAttribute)
from .constants import REGEX_STRING
from .exceptions import BlameLineParserError, BlameLineAttributeParserError
from .git_env import LocationContextExtensible


# TODO: ADD WAY TO INCLUDE FILE IN OUTPUT DATA
class BlameLine(LocationContextExtensible):
    parse_attributes = [
        ParsedAttribute('commit', 0, title='Commit'),
        ParsedAttribute('contributor', 1, title='Contributor'),
        IntegerParsedAttribute('line_no', 9, title='Line No.'),
        DateTimeParsedAttribute(
            name='datetime',
            regex_index=[2, 3, 4, 5, 6, 7],
            critical=False,
            title='Date/Time'
        ),
        ParsedAttribute('code', 10, title='Code'),
    ]

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    def __new__(cls, data, **kwargs):
        instance = super(BlameLine, cls).__new__(cls)
        try:
            instance.__init__(data, **kwargs)
        except BlameLineParserError as e:
            return e
        return instance

    def __str__(self):
        return f"<Line contributor={self.contributor} code={self.code}>"

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        regex_result = re.search(REGEX_STRING, value)
        if regex_result is None:
            # Sometimes, the result of the git-blame will be an empty string.
            # We should just ignore those for now.
            silent = value == ""
            raise BlameLineParserError(
                data=value,
                context=self.context,
                silent=silent
            )
        groups = regex_result.groups()
        for attr in self.parse_attributes:
            try:
                parsed_value = attr.parse(value, groups, self.context)
            except BlameLineAttributeParserError as e:
                if not e.critical:
                    click.echo(e.non_critical_message)
                    setattr(self, attr.name, None)
                else:
                    # Raising the exception will cause the overall line to be
                    # excluded.
                    raise e
            else:
                setattr(self, attr.name, parsed_value)

    def csv_row(self, output_cols):
        return [getattr(self, c) for c in output_cols]

import re

from git_blame_project import utils

from .attributes import (
    ParsedAttribute, IntegerParsedAttribute, DateTimeParsedAttribute,
    DependentAttribute, ExistingLineAttribute)
from .constants import REGEX_STRING
from .exceptions import BlameLineParserError, BlameLineAttributeParserError
from .git_env import LocationContextExtensible


def get_file_type(v):
    if v.suffix is None or v.suffix == "":
        # This can happen if the file is just an extension, like `.gitignore`
        # or `.npmrc`.
        if len(v.parts) != 0 and v.parts[-1].startswith('.'):
            return utils.standardize_extension(v.parts[-1], include_prefix=False)
    return utils.standardize_extension(v.suffix, include_prefix=False)


class BlameLine(LocationContextExtensible):
    attributes = [
        ExistingLineAttribute(name='file_name', title='File Name'),
        ExistingLineAttribute(
            attr='repository_file_path',
            name='file_type',
            title='File Type',
            formatter=get_file_type
        ),
        ExistingLineAttribute(
            attr='repository_file_path',
            name='file_path',
            title='File Path',
            formatter=lambda v: str(v)
        ),
        ParsedAttribute('commit', 0, title='Commit'),
        ParsedAttribute('contributor', 1, title='Contributor'),
        IntegerParsedAttribute('line_no', 9, title='Line No.'),
        DateTimeParsedAttribute(
            name='datetime',
            regex_index=[2, 3, 4, 5, 6, 7],
            critical=False,
            title='Date/Time'
        ),
        DependentAttribute(
            name='date',
            title='Date',
            parse=lambda params: params['datetime'].date()
        ),
        ParsedAttribute('code', 10, title='Code'),
    ]
    parsed_attributes = [a for a in attributes if isinstance(a, ParsedAttribute)]
    dependent_attributes = [
        a for a in attributes
        if isinstance(a, DependentAttribute)
    ]

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self._data = data
        self.data = data

    def __new__(cls, data, **kwargs):
        instance = super(BlameLine, cls).__new__(cls)
        try:
            instance.__init__(data, **kwargs)
        except BlameLineParserError as e:
            return e
        return instance

    def __str__(self):
        return f"<Line {self.data}>"

    def __repr__(self):
        return f"<Line {self.data}>"

    @classmethod
    def get_attribute(cls, name):
        try:
            return [
                attr for attr in cls.attributes
                if attr.name.lower() == name.lower()
            ][0]
        except IndexError as e:
            raise LookupError(
                f"No attribute exists with name {name}."
            ) from e

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

        # First, we parse the raw values that are derived directly from the
        # regex string.
        parsed_values = {}
        for attr in self.parsed_attributes:
            try:
                parsed_value = attr.parse(value, groups, self.context)
            except BlameLineAttributeParserError as e:
                if not e.critical:
                    setattr(self, attr.name, None)
                else:
                    # Raising the exception will cause the overall line to be
                    # excluded.
                    raise e
            else:
                attr.save(self, parsed_value)
                parsed_values[attr.name] = parsed_value

        # Now that we have the parsed values from the regex string, we
        # determine what the dependent attribute values are, as those depend
        # on the parsed attributes.
        for attr in self.dependent_attributes:
            if isinstance(attr, ExistingLineAttribute):
                parsed_value = attr.parse(self)
            else:
                parsed_value = attr.parse(parsed_values)
            attr.save(self, parsed_value)

    def csv_row(self, output_cols):
        return [getattr(self, c) for c in output_cols]

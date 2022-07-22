from git_blame_project.exceptions import GitBlameProjectError
from .git_env import LocationContextExtensible


class ParserError(GitBlameProjectError, LocationContextExtensible):
    def __init__(self, detail=None, silent=False, **kwargs):
        super().__init__(detail=detail)
        LocationContextExtensible.__init__(self, **kwargs)
        self._silent = silent

    @property
    def silent(self):
        return self._silent


class BlameLineParserError(ParserError):
    detail_prefix = "Line"

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self._data = data

    @property
    def detail(self):
        return self._data

    @property
    def content(self):
        return f"The line in file {self.repository_name} could not be parsed."


class BlameLineAttributeParserError(BlameLineParserError):
    detail_prefix = [
        BlameLineParserError.detail_prefix,
        'Reason',
    ]

    def __init__(self, data, attr, critical=True, value=None, **kwargs):
        super().__init__(data, **kwargs)
        self._attr = attr
        self._critical = critical
        self._value = value

    @property
    def attr(self):
        return self._attr

    @property
    def critical(self):
        return self._critical

    @property
    def detail(self):
        if self._value is not None:
            return [
                super().detail,
                f"The value {self._value} is invalid."
            ]
        return super().detail

    @property
    def content(self):
        return f"The attribute `{self.attr}` could not be parsed from line " \
            f"in file {self.repository_name}."


class BlameFileParserError(ParserError):
    @property
    def content(self):
        return f"The file {self.repository_name} could not be parsed."

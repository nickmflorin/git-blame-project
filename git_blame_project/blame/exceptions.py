from git_blame_project.exceptions import GitBlameProjectError
from .git_env import LocationContextExtensible


class ParserError(GitBlameProjectError, LocationContextExtensible):
    message_prefix = "There was a parsing error"

    def __init__(self, detail=None, silent=False, **kwargs):
        super().__init__(detail=detail)
        LocationContextExtensible.__init__(self, **kwargs)
        self._silent = silent

    @property
    def silent(self):
        return self._silent


class BlameLineParserError(ParserError):
    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self._data = data

    @property
    def data(self):
        return self._data

    @property
    def content(self):
        return f"The line {self.data} in file {self.repository_name} " \
            "could not be parsed."


class BlameLineAttributeParserError(BlameLineParserError):
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
        root_detail = super().detail
        if root_detail is not None:
            return root_detail
        elif self._value is not None:
            return f"The value {self._value} is invalid."
        return None

    @property
    def content(self):
        return f"The attribute {self.attr} could not be parsed from line " \
            f"{self.data} in file {self.repository_name}."

    @property
    def non_critical_message(self):
        return (
            f"Warning: Attribute {self.attr} is being excluded from line.\n"
            f"{self.message}"
        )


class BlameFileParserError(ParserError):
    @property
    def content(self):
        return f"The file {self.repository_name} could not be parsed."

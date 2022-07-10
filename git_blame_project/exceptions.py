from .context import LocationContextExtensible


class GitBlameProjectError(Exception):
    pass


class FailedBlame(LocationContextExtensible):
    def __init__(self, detail=None, silent=False, **kwargs):
        self._detail = detail
        self._silent = silent
        super().__init__(**kwargs)

    @property
    def silent(self):
        return self._silent

    @property
    def base_message(self):
        return (
            "There was an error parsing the data in file "
            f"{self.repository_name}."
        )

    @property
    def detail(self):
        if self._detail is not None:
            return str(self._detail)
        return None

    @property
    def message(self):
        base = self.base_message
        if self.detail is not None:
            return base + f"\nDetail: {self.detail}"
        return base


class FailedBlameLine(FailedBlame):
    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self._data = data

    @property
    def data(self):
        return self._data

    @property
    def base_message(self):
        return f"The line {self.data} in file {self.repository_name} " \
            "could not be parsed."


class FailedBlameFile(FailedBlame):
    @property
    def base_message(self):
        return f"The file {self.repository_name} could not be parsed."


class BlameLineParserError(GitBlameProjectError, FailedBlameLine):
    def __init__(self, *args, **kwargs):
        super().__init__("")
        FailedBlameLine.__init__(self, *args, **kwargs)

    def __str__(self):
        return self.message

    def to_model(self):
        return FailedBlameLine(
            data=self.data,
            context=self.context,
            silent=self.silent,
            detail=self.detail
        )


class BlameFileParserError(GitBlameProjectError, FailedBlameFile):
    def __init__(self, *args, **kwargs):
        super().__init__("")
        FailedBlameFile.__init__(self, *args, **kwargs)

    def __str__(self):
        return self.message

    def to_model(self):
        return FailedBlameFile(
            context=self.context,
            silent=self.silent,
            detail=self.detail
        )

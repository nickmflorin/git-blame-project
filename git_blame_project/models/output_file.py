from .output_type import OutputType


class OutputFile:
    def __init__(self, path, raw_value, suffix=None):
        self._path = path
        self._raw_value = raw_value
        self._suffix = suffix

    def __str__(self):
        return str(self.path)

    @property
    def path(self):
        if self._suffix is None:
            return self._path
        return self._path.with_stem(self._path.stem + "-" + self._suffix)

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def directory(self):
        return self.path.parent

    @property
    def extension(self):
        return self.path.suffix

    def add_suffix(self, suffix):
        self._suffix = suffix

    def with_suffix(self, suffix):
        return OutputFile(
            path=self._path,
            raw_value=self._raw_value,
            suffix=suffix
        )

    def filepath(self, output_type, suffix=None):
        return self.infer_filename_from_output_type(output_type, suffix=suffix)

    def infer_filename_from_output_type(self, output_type, suffix=None):
        output_type = OutputType.for_slug(output_type)
        if suffix is not None:
            return output_type.format_filename(self.with_suffix(suffix).path)
        return output_type.format_filename(self.path)

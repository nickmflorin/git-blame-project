import subprocess

from .blame_line import BlameLine
from .exceptions import BlameFileParserError, BlameLineParserError
from .git_env import LocationContextExtensible


class BlameFile(LocationContextExtensible):
    def __init__(self, lines, errors, **kwargs):
        super().__init__(**kwargs)
        self._lines = lines
        self._errors = errors

    def __str__(self):
        return f"<BlameFile path={str(self.context.repository_file_path)}>"

    def __repr__(self):
        return f"<BlameFile path={str(self.context.repository_file_path)}>"

    @property
    def errors(self):
        return self._errors

    @property
    def lines(self):
        return self._lines

    @property
    def num_lines(self):
        return len(self.lines)

    def csv_rows(self, output_cols):
        return [line.csv_row(output_cols) for line in self._lines]

    @classmethod
    def create(cls, context):
        errors = []
        try:
            result = subprocess.check_output(
                ['git', 'blame', "%s" % context.absolute_file_path])
        except subprocess.CalledProcessError as error:
            return BlameFileParserError(context=context, detail=str(error))
        else:
            try:
                result = result.decode("utf-8")
            except UnicodeDecodeError as error:
                return BlameFileParserError(context=context, detail=str(error))

            blame_lines = []
            for raw_line in result.split("\n"):
                blamed = BlameLine(raw_line, context=context)
                if isinstance(blamed, BlameLineParserError):
                    if not blamed.silent:
                        errors.append(blamed.message)
                else:
                    blame_lines.append(blamed)
            return cls(blame_lines, errors, context=context)

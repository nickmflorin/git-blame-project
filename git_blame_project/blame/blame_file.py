import subprocess

from git_blame_project.stdout import warning

from .blame_line import BlameLine
from .exceptions import BlameFileParserError, BlameLineParserError
from .git_env import LocationContextExtensible


class BlameFile(LocationContextExtensible):
    def __init__(self, lines, **kwargs):
        super().__init__(**kwargs)
        self._lines = lines

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
        try:
            result = subprocess.check_output(
                ['git', 'blame', "%s" % context.absolute_file_path])
        except subprocess.CalledProcessError as error:
            return BlameFileParserError(context=context, detail=error)
        else:
            try:
                result = result.decode("utf-8")
            except UnicodeDecodeError as error:
                return BlameFileParserError(context=context, detail=error)

            blame_lines = []
            for raw_line in result.split("\n"):
                blamed = BlameLine(raw_line, context=context)
                if isinstance(blamed, BlameLineParserError):
                    if not blamed.silent:
                        warning(blamed.message)
                else:
                    blame_lines.append(blamed)
            return cls(blame_lines, context=context)

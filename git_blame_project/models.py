import collections
import csv
import os
import re
import subprocess
import pathlib

import click

from git_blame_project import constants

from .context import LocationContextExtensible, LocationContext
from .exceptions import (
    BlameLineParserError, BlameFileParserError, GitBlameProjectError,
    BlameLineAttributeParserError)
from .fs import repository_directory_context
from .stdout import warning
from .utils import ensure_datetime, DateTimeValueError


def get_git_branch(repository):
    with repository_directory_context(repository):
        result = subprocess.check_output(['git', 'branch'])
        try:
            result = result.decode("utf-8")
        except UnicodeDecodeError:
            warning(
                "There was an error determining the current git branch for "
                "purposes of auto-generating a filename.  A placeholder value "
                "will be used."
            )
            return "unknown"
        lines = [r.strip() for r in result.split("\n")]
        for line in lines:
            if line.startswith("*"):
                return line.split("*")[1].strip()
        warning(
            "There was an error determining the current git branch for "
            "purposes of auto-generating a filename.  A placeholder value "
            "will be used."
        )
        return "unknown"


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

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        regex_result = re.search(constants.REGEX_STRING, value)
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

    def __str__(self):
        return f"<Line contributor={self.contributor} code={self.code}>"


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
                        click.echo(blamed.message)
                else:
                    blame_lines.append(blamed)
            return cls(blame_lines, context=context)


class Blame:
    def __init__(self, repository, **kwargs):
        self._repository = repository
        self._files = []
        self._ignore_dirs = kwargs.pop('ignore_dirs', None)
        self._ignore_file_types = kwargs.pop('ignore_file_types', None)
        self._dry_run = kwargs.pop('dry_run', False)
        self._filelimit = kwargs.pop('filelimit', None)
        self._outputcols = kwargs.pop('outputcols', None)
        self._outputdir = kwargs.pop('outputdir', None)
        self._outputfile = kwargs.pop('outputfile', None)

    @property
    def files(self):
        if not hasattr(self, '_files'):
            raise GitBlameProjectError("Blame has not yet been performed.")
        return self._files

    @property
    def filelimit(self):
        return self._filelimit

    @property
    def num_lines(self):
        return sum(f.num_lines for f in self.files)

    @property
    def dry_run(self):
        return self._dry_run

    @property
    def repository(self):
        return pathlib.Path(self._repository)

    @property
    def ignore_dirs(self):
        if self._ignore_dirs is not None:
            return self._ignore_dirs + constants.DEFAULT_IGNORE_DIRECTORIES
        return constants.DEFAULT_IGNORE_DIRECTORIES

    @property
    def outputcols(self):
        if self._outputcols is None:
            return [p.name for p in BlameLine.parse_attributes]
        return self._outputcols

    @classmethod
    def transform_file_types(cls, file_types):
        transformed = []
        for file_type in file_types:
            if not file_type.startswith('.'):
                transformed.append(f".{file_type.lower()}")
            else:
                transformed.append(file_type.lower())
        return transformed

    @property
    def ignore_file_types(self):
        if self._ignore_file_types is not None:
            return self.transform_file_types(
                self._ignore_file_types + constants.DEFAULT_IGNORE_FILE_TYPES)
        return self.transform_file_types(constants.DEFAULT_IGNORE_FILE_TYPES)

    @property
    def outputdir(self):
        if self._outputdir is None:
            return pathlib.Path(os.getcwd())
        return self._outputdir

    @property
    def outputfile(self):
        # The output file is guaranteed to be an existent directory or a file
        # that may or may not exist in a parent directory that does exist.
        if self._outputfile is None:
            branch_name = get_git_branch(self.repository)
            return self.outputdir / f"{self.outputdir.parts[-1]}-{branch_name}.csv"
        elif self._outputfile.is_dir():
            branch_name = get_git_branch(self.repository)
            return self._outputfile / f"{self.outputdir.parts[-1]}-{branch_name}.csv"
        return self._outputfile

    def __call__(self):
        setattr(self, '_files', [])

        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            self._perform_blame()
        self.output()

    def output(self):
        click.echo(f"Writing to {str(self.outputfile)}")
        with open(str(self.outputfile), 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow([attr.title for attr in BlameLine.parse_attributes])
            for file in self.files:
                writer.writerows(file.csv_rows(self.outputcols))

    def _perform_blame(self):
        blame_count = 0
        for path, _, files in os.walk(self.repository):
            for name in files:
                file_dir = pathlib.Path(path)
                if any([p in self.ignore_dirs for p in file_dir.parts]):
                    continue

                file_path = file_dir / name
                if file_path.suffix.lower() in self.ignore_file_types:
                    continue

                repository_path = file_dir.relative_to(self.repository)
                context = LocationContext(
                    repository=self.repository,
                    repository_path=repository_path,
                    name=name
                )
                blamed_file = BlameFile.create(context)
                if isinstance(blamed_file, BlameFileParserError):
                    if not blamed_file.silent:
                        click.echo(blamed_file.message)
                else:
                    self._files.append(blamed_file)
                    blame_count += 1
                    if blame_count >= self.filelimit:
                        return

    def count_lines_by_attr(self, attr, formatter=None):
        count = collections.defaultdict(int)
        for file in self.files:
            for line in file.lines:
                count[getattr(line, attr)] += 1
        final_data = {}
        for k, v in count.items():
            if formatter is not None:
                final_data[k] = formatter(v)
            else:
                final_data[k] = v
        return final_data

    def get_contributions_by_line(self, format_as_percentage=True):
        def pct_formatter(v):
            return "{:.12%}".format((v / self.num_lines))
        return self.count_lines_by_attr(
            attr='contributor',
            formatter=pct_formatter if format_as_percentage else None
        )

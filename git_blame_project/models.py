import collections
import os
import re
import subprocess
import pathlib

import click

from .context import LocationContextExtensible, LocationContext
from .exceptions import (
    BlameLineParserError, BlameFileParserError, FailedBlameLine,
    FailedBlameFile)
from .utils import ensure_datetime, DateTimeValueError


DEFAULT_IGNORE_DIRECTORIES = ['.git']
DEFAULT_IGNORE_FILE_TYPES = [".png", ".jpeg", ".jpg", ".gif", ".svg"]


COMMIT_REGEX = r"([\^a-zA-Z0-9]*)"
DATE_REGEX = r"([0-9]{4})-([0-9]{2})-([0-9]{2})"
TIME_REGEX = r"([0-9]{2}):([0-9]{2}):([0-9]{2})"

REGEX_STRING = COMMIT_REGEX \
    + r"\s*\(([a-zA-Z0-9\s]*)\s*" \
    + DATE_REGEX + r"\s*" \
    + TIME_REGEX + r"\s*" \
    + r"([-+0-9]*)\s*([0-9]*)\)\s*(.*)"


class BlameLine(LocationContextExtensible):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

        if len(args) == 1 or 'data' in kwargs:
            data = kwargs.pop('data', None)
            if args:
                data = args[0]
            kw = self.kwargs_from_data(data, context=self.context)
        else:
            kw = dict(*args, **kwargs)

        self._code = kw.pop('code')
        self._commit = kw.pop('commit')
        self._collaborator = kw.pop('collaborator')
        self._dt = kw.pop('dt')
        self._line_no = kw.pop('line_no')

    def __new__(cls, *args, **kwargs):
        instance = super(BlameLine, cls).__new__(cls)
        try:
            instance.__init__(*args, **kwargs)
        except BlameLineParserError as e:
            return e.to_model()
        return instance

    @property
    def csv_row(self):
        return [self._collaborator, self._code]

    @property
    def line_no(self):
        try:
            return int(self._line_no)
        except ValueError:
            print("ERROR")
            return None

    @property
    def collaborator(self):
        return self._collaborator

    @property
    def dt(self):
        return self._dt

    @property
    def commit(self):
        return self._commit

    @property
    def code(self):
        return self._code

    def __str__(self):
        return f"<Line collaborator={self._collaborator} code={self._code}>"

    @classmethod
    def datetime_from_data(cls, data, groups, context):
        try:
            datetime_string = f"{groups[2]}-{groups[3]}-{groups[4]} " \
                + f"{groups[5]}:{groups[6]}:{groups[7]}"
            return ensure_datetime(datetime_string)
        except IndexError as e:
            raise BlameLineParserError(data=data, context=context) from e
        except DateTimeValueError as e:
            # TODO: We might want to lax this so that the date is just not
            # included.
            raise BlameLineParserError(
                context=context,
                data=data,
                reason="The datetime of the blame could not be parsed."
            ) from e

    @classmethod
    def kwargs_from_data(cls, data, context):
        result = re.search(REGEX_STRING, data)
        if result is None:
            silent = data == ""
            raise BlameLineParserError(
                data=data,
                context=context,
                # Sometimes, the result of the git-blame will be an empty string.
                # We should just ignore those for now.
                silent=silent
            )
        groups = result.groups()
        try:
            return dict(
                commit=groups[0].strip(),
                collaborator=groups[1].strip(),
                dt=cls.datetime_from_data(data, groups, context),
                line_no=groups[9].strip(),
                code=groups[10].strip(),
            )
        except IndexError as e:
            raise BlameLineParserError(data=data, context=context) from e


class BlameFile(LocationContextExtensible):
    def __init__(self, lines, **kwargs):
        super().__init__(**kwargs)
        self._lines = lines

    # def __call__(self):
    #     self._lines = []

    @property
    def lines(self):
        return self._lines

    @property
    def csv_rows(self):
        return [line.csv_row for line in self._lines]

    @classmethod
    def create(cls, context):
        if any([
            p in DEFAULT_IGNORE_DIRECTORIES
            for p in context.repository_path.parts
        ]):
            return None
        try:
            result = subprocess.check_output(
                ['git', 'blame', "%s" % context.absolute_file_path])
        except subprocess.CalledProcessError as error:
            return FailedBlameFile(context=context, detail=error)
        else:
            try:
                result = result.decode("utf-8")
            except UnicodeDecodeError as error:
                return FailedBlameFile(context=context, detail=error)

            blame_lines = []
            for raw_line in result.split("\n"):
                # if raw_line != "":
                blamed = BlameLine(raw_line, context=context)
                if blamed is not None:
                    if isinstance(blamed, FailedBlameLine):
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

    @property
    def files(self):
        return self._files

    @property
    def dry_run(self):
        return self._dry_run

    @property
    def repository(self):
        return pathlib.Path(self._repository)

    @property
    def ignore_dirs(self):
        if self._ignore_dirs is not None:
            return self._ignore_dirs + DEFAULT_IGNORE_DIRECTORIES
        return DEFAULT_IGNORE_DIRECTORIES

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
                self._ignore_file_types + DEFAULT_IGNORE_FILE_TYPES)
        return self.transform_file_types(DEFAULT_IGNORE_FILE_TYPES)

    def analyze_contributors(self):
        total_lines = 0
        count = collections.defaultdict(int)
        for file in self.files:
            for line in file.lines:
                count[line.collaborator] += 1
                total_lines += 1
        final_data = {}
        for k, v in count.items():
            final_data[k] = "{:.12%}".format((v / total_lines))
        print(final_data)

    def __call__(self):
        self._files = []

        os.chdir(self.repository)

        breaknum = 0

        # import ipdb; ipdb.set_trace()
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
                if isinstance(blamed_file, FailedBlameFile):
                    if not blamed_file.silent:
                        click.echo(blamed_file.message)
                else:
                    self._files.append(blamed_file)
                    breaknum += 1
                    if breaknum > 100:
                        return

        # print("WRITING CSV")

        # with open('/Users/nick/Desktop/test.csv', 'w') as csvfile:
        #     writer = csv.writer(csvfile, delimiter=',')
        #     writer.writerow(["Contributor", "Code"])
        #     for file in self._files:
        #         print(file.csv_rows)
        #         writer.writerows(file.csv_rows)


import collections
import csv
import os
import pathlib

import click

from git_blame_project import constants

from .blame_file import BlameFile
from .blame_line import BlameLine
from .exceptions import BlameFileParserError
from .git_env import (
    get_git_branch, repository_directory_context, LocationContext)


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
            raise TypeError(
                "The Blame has not been performed yet and there are no files "
                "that have been parsed."
            )
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
    def default_outputfile(self):
        branch_name = get_git_branch(self.repository)
        return f"{self.outputdir.parts[-1]}-{branch_name}.csv"

    @property
    def outputfile(self):
        # The output file is guaranteed to be an existing directory or a file
        # that may or may not exist, but in a parent directory that does exist.
        if self._outputfile is None:
            return self.outputdir / self.default_outputfile
        elif self._outputfile.is_dir():
            return self._outputfile / self.default_outputfile
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

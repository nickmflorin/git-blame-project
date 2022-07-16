import os
import pathlib

import click

from git_blame_project.models import OutputTypes

from .analysis import Analyses, LineBlameAnalysis
from .blame_file import BlameFile
from .blame_line import BlameLine
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import repository_directory_context, LocationContext


class Blame:
    cli_arguments = [
        'ignore_dirs', 'ignore_file_types', 'dry_run', 'file_limit',
        'line_blame_columns', 'output_dir', 'output_file', 'output_type',
        'analysis'
    ]

    def __init__(self, repository, **kwargs):
        self._repository = repository
        for argument in self.cli_arguments:
            setattr(self, f'_{argument}', kwargs.pop(argument, None))

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            files = self.perform_blame()

        self.analysis(files)
        if self.should_output:
            self.analysis.output(self)

    @property
    def file_limit(self):
        return self._file_limit

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

    @property
    def line_blame_columns(self):
        if self._line_blame_columns is None:
            return [p.name for p in BlameLine.attributes]
        return self._line_blame_columns

    @property
    def output_type(self):
        if self._output_type is not None:
            return self._output_type
        elif self._output_file is not None:
            return OutputTypes.from_extensions(self._output_file.extension)
        # TODO: Should we return the default?  Or should this represent a case
        # where we do not output?
        return OutputTypes.all()

    @property
    def analysis(self):
        if self._analysis is None:
            return Analyses(LineBlameAnalysis())
        return self._analysis

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

    @property
    def output_dir(self):
        if self._output_dir is None:
            return pathlib.Path(os.getcwd())
        return self._output_dir

    @property
    def should_output(self):
        return self._output_dir is not None or self._output_file is not None \
            or self._output_type is not None

    def perform_blame(self):
        blame_count = 0
        blame_files = []
        for path, _, files in os.walk(self.repository):
            for file_name in files:
                # This seems to be happening occasionally with paths that are
                # in directories that typically should be ignored (like .git).
                if file_name == "None":
                    continue
                file_dir = pathlib.Path(path)
                if any([p in self.ignore_dirs for p in file_dir.parts]):
                    continue

                file_path = file_dir / file_name
                if file_path.suffix.lower() in self.ignore_file_types:
                    continue

                repository_path = file_dir.relative_to(self.repository)
                context = LocationContext(
                    repository=self.repository,
                    repository_path=repository_path,
                    file_name=file_name
                )
                blamed_file = BlameFile.create(context)
                if isinstance(blamed_file, BlameFileParserError):
                    if not blamed_file.silent:
                        click.echo(blamed_file.message)
                else:
                    blame_files.append(blamed_file)
                    blame_count += 1
                    if self.file_limit is not None \
                            and blame_count >= self.file_limit:
                        return blame_files
        return blame_files

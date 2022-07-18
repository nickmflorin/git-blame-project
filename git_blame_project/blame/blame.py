import os
import pathlib

import click

from git_blame_project.stdout import Terminal, warning, info
from git_blame_project.utils import standardize_extensions

from .analysis import Analyses, LineBlameAnalysis
from .blame_file import BlameFile
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import repository_directory_context, LocationContext


class Blame:
    cli_arguments = [
        'ignore_dirs', 'ignore_file_types', 'file_limit', 'analyses']

    def __init__(self, repository, **kwargs):
        self._repository = repository
        for argument in self.cli_arguments:
            setattr(self, f'_{argument}', kwargs.pop(argument, None))

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            files = self.perform_blame()
        self.analyses(files)

    @property
    def file_limit(self):
        return self._file_limit

    @property
    def repository(self):
        return pathlib.Path(self._repository)

    @property
    def ignore_dirs(self):
        if self._ignore_dirs is not None:
            return set(self._ignore_dirs + DEFAULT_IGNORE_DIRECTORIES)
        return set(DEFAULT_IGNORE_DIRECTORIES)

    @property
    def analyses(self):
        if self._analyses is None:
            return Analyses(LineBlameAnalysis())
        return self._analyses

    @property
    def ignore_file_types(self):
        if self._ignore_file_types is not None:
            return standardize_extensions(
                self._ignore_file_types + DEFAULT_IGNORE_FILE_TYPES)
        return standardize_extensions(DEFAULT_IGNORE_FILE_TYPES)

    def perform_blame(self):
        blame_files = []

        info("Filtering out files that should be ignored.")
        flattened_files = []

        info("Collecting Files in the Repository")
        flattened_files = []
        for path, _, files in os.walk(self.repository):
            file_dir = pathlib.Path(path)
            for file_name in files:
                flattened_files.append((file_dir, file_name))

        limit = self.file_limit or len(flattened_files)
        filtered_files = []

        with click.progressbar(
            length=limit,
            label=Terminal.message('Filtering Files', color="blue"),
            color='blue'
        ) as progress_bar:
            for file_dir, file_name in flattened_files:
                file_path = file_dir / file_name
                # This seems to be happening occasionally with paths that are
                # in directories that typically should be ignored (like .git).
                if file_name == "None":
                    if self.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                elif any([p in self.ignore_dirs for p in file_dir.parts]):
                    if self.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                elif file_path.suffix.lower() in self.ignore_file_types:
                    if self.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                filtered_files.append((file_dir, file_name))
                progress_bar.update(1)
                if self.file_limit is not None \
                        and len(filtered_files) == self.file_limit:
                    break

        errors = []
        with click.progressbar(
            filtered_files,
            label=Terminal.message(
                'Performing Blame on Each File', color="blue"),
            color='blue',
            length=len(filtered_files)
        ) as progress_bar:
            for file_dir, file_name in progress_bar:
                repository_path = file_dir.relative_to(self.repository)
                context = LocationContext(
                    repository=self.repository,
                    repository_path=repository_path,
                    file_name=file_name
                )
                blamed_file = BlameFile.create(context)
                if isinstance(blamed_file, BlameFileParserError):
                    if not blamed_file.silent:
                        errors.append(blamed_file)
                else:
                    blame_files.append(blamed_file)

        if errors:
            for error in errors:
                warning(error.message)
        return blame_files

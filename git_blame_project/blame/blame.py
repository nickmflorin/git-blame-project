import os
import pathlib

import click

from git_blame_project import stdout
from git_blame_project.models import Configurable, Config
from git_blame_project.utils import standardize_extensions

from .analysis import Analyses, LineBlameAnalysis
from .blame_file import BlameFile
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import repository_directory_context, LocationContext


class Blame(Configurable):
    configuration = [
        Config(
            name='ignore_dirs',
            default=set(DEFAULT_IGNORE_DIRECTORIES),
            formatter=lambda v: set(v + DEFAULT_IGNORE_DIRECTORIES)
        ),
        Config(
            name='ignore_file_types',
            default=standardize_extensions(DEFAULT_IGNORE_FILE_TYPES),
            formatter=lambda v: set(standardize_extensions(
                v + DEFAULT_IGNORE_FILE_TYPES))
        ),
        Config(name='file_limit'),
        Config(name='analyses', default=Analyses(LineBlameAnalysis()))
    ]

    def __init__(self, repository, **kwargs):
        super().__init__(config=kwargs)
        self._repository = repository

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            files = self.perform_blame()
        self.config.analyses(files)

    @property
    def repository(self):
        return pathlib.Path(self._repository)

    def perform_blame(self):
        blame_files = []

        stdout.info("Filtering out files that should be ignored.")
        flattened_files = []

        stdout.info("Collecting Files in the Repository")
        flattened_files = []
        for path, _, files in os.walk(self.repository):
            file_dir = pathlib.Path(path)
            for file_name in files:
                flattened_files.append((file_dir, file_name))

        limit = len(flattened_files)
        if self.config.file_limit is not None:
            limit = min(self.config.file_limit, limit)

        filtered_files = []

        with click.progressbar(
            length=limit,
            label=stdout.info('Filtering Files', display=False),
            color='blue'
        ) as progress_bar:
            for file_dir, file_name in flattened_files:
                file_path = file_dir / file_name
                # This seems to be happening occasionally with paths that are
                # in directories that typically should be ignored (like .git).
                if file_name == "None":
                    if self.config.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                elif any([p in self.config.ignore_dirs for p in file_dir.parts]):
                    if self.config.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                elif file_path.suffix.lower() in self.config.ignore_file_types:
                    if self.config.file_limit is None:
                        # If there is a file limit, we only want to update the
                        # progress bar when we encounter a valid file.
                        progress_bar.update(1)
                    continue

                filtered_files.append((file_dir, file_name))
                progress_bar.update(1)
                if self.config.file_limit is not None \
                        and len(filtered_files) == self.config.file_limit:
                    break

        file_errors = []
        errors = []
        with click.progressbar(
            filtered_files,
            label=stdout.info('Performing Blame on Each File', display=False),
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
                        file_errors.append(blamed_file)
                else:
                    if blamed_file.errors:
                        errors += blamed_file.errors
                    blame_files.append(blamed_file)

        if file_errors:
            stdout.warning(
                f"There were {len(file_errors)} files that could not be parsed:")
            for error in file_errors:
                stdout.warning(error.message)
        if errors:
            stdout.warning(
                f"There were {len(errors)} lines that could not be parsed:")
            for error in errors:
                stdout.warning(error.message)
        return blame_files

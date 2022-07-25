import os
import pathlib

import click

from git_blame_project import utils, configurable

from .analysis import Analyses, LineBlameAnalysis
from .blame_file import BlameFile
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import repository_directory_context, LocationContext


class Blame(configurable.Configurable):
    configure_on_init = True
    configuration = [
        configurable.Config(
            param='ignore_dirs',
            default=list(set(DEFAULT_IGNORE_DIRECTORIES)),
            formatter=lambda v: set(list(v) + DEFAULT_IGNORE_DIRECTORIES)
        ),
        configurable.Config(
            param='ignore_file_types',
            default=utils.standardize_extensions(DEFAULT_IGNORE_FILE_TYPES),
            formatter=lambda v: set(utils.standardize_extensions(
                v + DEFAULT_IGNORE_FILE_TYPES))
        ),
        configurable.Config(param='file_limit'),
        configurable.Config(
            param='analyses',
            default=Analyses(LineBlameAnalysis())
        )
    ]

    def __init__(self, repository, **kwargs):
        super().__init__(**kwargs)
        self._repository = repository

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            files = self.perform_blame()
        self.analyses(files)

    @property
    def repository(self):
        return pathlib.Path(self._repository)

    def perform_blame(self):
        blame_files = []

        utils.stdout.info("Filtering out files that should be ignored.")
        flattened_files = []

        utils.stdout.info("Collecting Files in the Repository")
        flattened_files = []
        for path, _, files in os.walk(self.repository):
            file_dir = pathlib.Path(path)
            for file_name in files:
                flattened_files.append((file_dir, file_name))

        limit = len(flattened_files)
        if self.file_limit is not None:
            limit = min(self.file_limit, limit)

        filtered_files = []

        with click.progressbar(
            length=limit,
            label=utils.stdout.info('Filtering Files', display=False),
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

        file_errors = []
        errors = []
        with click.progressbar(
            filtered_files,
            label=utils.stdout.info(
                'Performing Blame on Each File', display=False),
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
            utils.stdout.warning(
                f"There were {len(file_errors)} files that could not be parsed:")
            for error in file_errors:
                utils.stdout.warning(error.message)
        if errors:
            utils.stdout.warning(
                f"There were {len(errors)} lines that could not be parsed:")
            for error in errors:
                utils.stdout.warning(error.message)
        return blame_files

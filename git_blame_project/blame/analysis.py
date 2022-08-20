import csv
import os
import pathlib

import click

from git_blame_project import utils, configurable
from git_blame_project.models import OutputTypes, OutputType

from .blame_file import BlameFile
from .blame_line import BlameLine
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import repository_directory_context, LocationContext
from .git_env import get_git_branch
from .utils import (
    TabularData,
    tabulate_nested_attribute_data
)


__all__ = ('LineBlameAnalysis', 'BreakdownAnalysis')


class Analysis(configurable.Configurable):
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
                list(v) + DEFAULT_IGNORE_FILE_TYPES))
        ),
        configurable.Config(param='file_limit'),
        configurable.Config(param='dry_run', default=False),
        configurable.Config(
            param='repository',
            required=True,
            formatter=utils.path_formatter()
        ),
        configurable.Config(param='output_file', required=False),
        configurable.Config(param='output_type', required=False),
        configurable.Config(param='output_dir', default=utils.LazyFn(
            func=pathlib.Path,
            args=[os.getcwd]
        ))
    ]

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            self._files = self.perform_blame()
        self._result = self.get_result()
        if self.should_output:
            self.output()

    @property
    def result(self):
        if not getattr(self, '_result', None):
            raise Exception("The analysis has not yet been performed.")
        return self._result

    @property
    def files(self):
        if not getattr(self, '_files', None):
            raise Exception("The analysis has not yet been performed.")
        return self._files

    @property
    def should_output(self):
        return self.output_dir is not None \
            or self.output_file is not None \
            or self.output_type is not None

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

    def get_lines(self):
        for file in self.files:
            for line in file.lines:
                yield line

    def get_result(self):
        raise NotImplementedError()

    @property
    def output_type(self):
        if self.output_type is not None:
            return self.output_type
        elif self.output_file is not None:
            return OutputTypes.from_extensions(self.output_file.extension)
        # TODO: Should we return the default?  Or should this represent a case
        # where we do not output?
        return OutputTypes.all()

    def output(self):
        output_mapping = {
            OutputTypes.CSV.slug: self.output_csv,
            OutputTypes.EXCEL.slug: self.output_excel,
        }
        for output_type in self.output_type:
            output_mapping[output_type.slug]()

    def default_output_file_name(self, suffix=None):
        branch_name = get_git_branch(self.repository)
        if suffix is None and getattr(self, 'output_file_suffix'):
            suffix = self.output_file_suffix
        if suffix is not None:
            return (
                f"{self.output_dir.parts[-1]}-{branch_name}-"
                f"{suffix}"
            )
        return f"{self.output_dir.parts[-1]}-{branch_name}"

    def default_output_file_path(self, output_type, suffix=None):
        return OutputType.for_slug(output_type) \
            .format_filename(self.default_output_file_name(suffix=suffix))

    def output_file_path(self, output_type):
        # This used to be used when running multiple analyses from the same
        # command, but is not used anymore.
        suffix = None
        if getattr(self, 'output_file_suffix', None):
            suffix = self.output_file_suffix

        self.default_output_file_name('csv')

        # The output file is guaranteed to be an existing directory or a file
        # that may or may not exist, but in a parent directory that does exist.
        if self.output_file is not None:
            return self.output_file.filepath(output_type, suffix=suffix)
        return self.output_dir / self.default_output_file_path(
            output_type=output_type,
            suffix=suffix
        )

    def output_csv(self):
        output_file = self.output_file_path('csv')
        utils.stdout.info(f"Writing to {str(output_file)}")
        if not self.dry_run:
            with open(str(output_file), 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(self.result.header)
                writer.writerows(self.result.rows)

    def output_excel(self):
        utils.stdout.not_supported(
            "The `excel` output type is not yet supported.")


class LineBlameAnalysis(Analysis):
    configuration = [
        configurable.Config(
            param='columns',
            default=[p.name for p in BlameLine.attributes]
        )
    ]

    def get_result(self):
        rows = []
        for file in self.files:
            rows += file.csv_rows(self.columns)
        return TabularData(
            header=[
                attr.title for attr in BlameLine.attributes
                if attr.name in self.columns
            ],
            rows=rows
        )


class BreakdownAnalysis(Analysis):
    configuration = [
        configurable.Config(param='attributes', required=True)
    ]

    def get_result(self):
        def pct_formatter(v):
            num_lines = sum(f.num_lines for f in self.files)
            return "{:.12%}".format((v / num_lines))
        return tabulate_nested_attribute_data(
            self.get_lines,
            *self.attributes,
            formatter=pct_formatter,
            formatted_title='Contributions'
        )

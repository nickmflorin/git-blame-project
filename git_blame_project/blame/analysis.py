import collections
import csv
import os
import pathlib

from git_blame_project import utils, configurable
from git_blame_project.models import OutputTypes, OutputType

from .blame_file import BlameFile
from .blame_line import BlameLine
from .constants import DEFAULT_IGNORE_DIRECTORIES, DEFAULT_IGNORE_FILE_TYPES
from .exceptions import BlameFileParserError
from .git_env import (
    repository_directory_context, LocationContext, get_git_branch)


__all__ = ('LineBlameAnalysis', 'BreakdownAnalysis')


TabularData = collections.namedtuple('TabularData', ['header', 'rows'])


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

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self._file_count = 0
    #     self._line_count = 0

    def __call__(self):
        # We must physically move to the directory that the repository is
        # located in such that we can access the `git` command line tools.
        with repository_directory_context(self.repository):
            result = self.get_result()
        if self.should_output:
            self.output(result)

    # @property
    # def result(self):
    #     if not getattr(self, '_result', None):
    #         raise Exception("The analysis has not yet been performed.")
    #     return self._result

    # @property
    # def files(self):
    #     if not getattr(self, '_files', None):
    #         raise Exception("The analysis has not yet been performed.")
    #     return self._files

    @property
    def should_output(self):
        return self.output_dir is not None \
            or self.output_file is not None \
            or self.output_type is not None

    def get_files(self):
        count = 0
        for path, _, files in os.walk(self.repository):
            file_dir = pathlib.Path(path)
            for file_name in files:
                file_path = file_dir / file_name
                # This seems to be happening occasionally with paths that are
                # in directories that typically should be ignored (like .git).
                if file_name == "None":
                    continue
                if any([p in self.ignore_dirs for p in file_dir.parts]):
                    continue
                if file_path.suffix.lower() in self.ignore_file_types:
                    continue

                yield (file_dir, file_name)

                if self.file_limit is not None and count == self.file_limit:
                    return
                count += 1

    def generate_files(self):
        file_errors = []
        errors = []
        blame_files = []

        with utils.Spinner(
                label=utils.stdout.info('Analyzing Files', display=False)):
            for file_dir, file_name in self.get_files():
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
                    yield blamed_file

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

    def generate_lines(self):
        for file in self.generate_files():
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

    def output(self, result):
        output_mapping = {
            OutputTypes.CSV.slug: self.output_csv,
            OutputTypes.EXCEL.slug: self.output_excel,
        }
        for output_type in self.output_type:
            output_mapping[output_type.slug](result)

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

    def output_csv(self, result):
        output_file = self.output_file_path('csv')
        utils.stdout.info(f"Writing to {str(output_file)}")
        if not self.dry_run:
            with open(str(output_file), 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(result.header)
                writer.writerows(result.rows)

    def output_excel(self, result):
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
        for file in self.generate_files():
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

    def _perform_count(self, line, current, *attributes):
        attr_value = getattr(line, attributes[0].name)
        current.setdefault(attr_value, {'count': 0, 'children': {}})
        current[attr_value]['count'] += 1
        if len(attributes) > 1:
            self._perform_count(
                line,
                current[attr_value]['children'],
                *attributes[1:],
            )

    def get_result(self):
        count = {}
        num_lines = 0
        for line in self.generate_lines():
            self._perform_count(line, count, *self.attributes)
            num_lines += 1

        def pct_formatter(v):
            if num_lines != 0:
                return "{:.12%}".format((v / num_lines))
            # This should not happen because it would imply there were no lines
            # for the given attribute, but just in case we implement this check.
            return "{:.12%}".format(0.0)

        return self.tabulate_nested_attribute_data(
            count,
            formatter=pct_formatter,
            formatted_title='Contributions'
        )

    def tabulate_nested_attribute_data(self, data, formatter=None,
            formatted_title="Formatted"):
        def get_row(value, attribute_count, level_number=0):
            row = []
            assert level_number <= len(self.attributes), \
                f"The current level number {level_number} should always be " \
                f"less than the number of attributes, {len(self.attributes)}."
            # Add the cells at the beginning of the row that display the
            # attribute at the current nested level.
            for i in range(len(self.attributes)):
                if level_number == i:
                    row.append(value)
                else:
                    row.append("")
            if formatter is not None:
                return row + [
                    attribute_count['count'],
                    formatter(attribute_count['count'])
                ]
            return row + [attribute_count['count']]

        def get_rows(data, level_number=0):
            rows = []
            for k, v in data.items():
                rows.append(get_row(k, v, level_number=level_number))
                if len(v['children']) != 0:
                    rows += get_rows(
                        data=v['children'],
                        level_number=level_number + 1
                    )
            return rows

        header = [attr.title for attr in self.attributes] + ["Num Lines"]
        if formatter is not None:
            header += [formatted_title]

        return TabularData(
            header=header,
            rows=get_rows(data=data)
        )

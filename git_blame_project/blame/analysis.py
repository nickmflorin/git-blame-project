import csv
import pathlib
import os

from git_blame_project import utils, configurable
from git_blame_project.models import Slug, OutputTypes, OutputType

from .blame_line import BlameLine
from .git_env import get_git_branch
from .utils import (
    TabularData,
    tabulate_nested_attribute_data,
    count_by_nested_attributes
)


def analyses(cls):
    if not hasattr(cls, '__call__'):
        raise TypeError(
            f"The analysis class {cls.__name__} must be callable."
        )
    original_call = getattr(cls, '__call__')

    def __call__(instance, files):
        setattr(instance, '_files', files)
        if hasattr(instance, '_result'):
            delattr(instance, '_result')
        result = original_call(instance)
        setattr(instance, '_result', result)
        return result

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

    setattr(cls, '__call__', __call__)
    setattr(cls, 'result', result)
    setattr(cls, 'files', files)
    return cls


def analysis(slug, configuration=None):
    def klass_decorator(cls):
        cls = analyses(cls)
        setattr(cls, 'slug', slug)
        if configuration is not None:
            setattr(cls, 'configuration', configuration)
        return cls
    return klass_decorator


class Analysis(Slug(
    plural_model='git_blame_project.blame.analysis.Analyses',
    configuration=[
        configurable.Config(param='dry_run', default=False),
        configurable.Config(
            param='repository',
            required=True,
            formatter=utils.path_formatter()
        ),
        configurable.Config(param='num_analyses', required=True),
        configurable.Config(param='output_file', required=False),
        configurable.Config(param='output_type', required=False),
        configurable.Config(param='output_dir', default=utils.LazyFn(
            func=pathlib.Path,
            args=[os.getcwd]
        ))
    ]
)):
    def get_lines(self):
        for file in self.files:
            for line in file.lines:
                yield line

    def count_lines_by_attr(self, *attrs, **kwargs):
        return count_by_nested_attributes(
            self.get_lines,
            *attrs,
            **kwargs
        )

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
        # The output file is guaranteed to be an existing directory or a file
        # that may or may not exist, but in a parent directory that does exist.
        suffix = None

        self.default_output_file_name('csv')
        if self.num_analyses > 1:
            if getattr(self, 'output_file_suffix', None):
                suffix = self.output_file_suffix
            else:
                suffix = self.slug
        if self.output_file is not None:
            return self.output_file.filepath(output_type, suffix=suffix)
        return self.output_dir / self.default_output_file_path(
            output_type=output_type,
            suffix=suffix
        )

    def output_csv(self):
        output_file = self.output_file_path('csv')
        utils.stdout.info(f"Writing to {str(output_file)}")

        if not hasattr(self, 'get_tabular_data'):
            raise TypeError(
                f"The analysis class {self.__class__} does not expose a "
                "method for retrieving the tabular data."
            )
        data = self.get_tabular_data()
        if not self.dry_run:
            with open(str(output_file), 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(data.header)
                writer.writerows(data.rows)

    def output_excel(self):
        utils.stdout.not_supported(
            "The `excel` output type is not yet supported.")


@analysis(slug='line_blame')
class LineBlameAnalysis(Analysis):
    configuration = [
        configurable.Config(
            param='columns',
            accessor='line_blame_columns',
            default=[p.name for p in BlameLine.attributes]
        )
    ]

    def __call__(self):
        return self.files

    def get_tabular_data(self):
        rows = []
        for file in self.result:
            rows += file.csv_rows(self.columns)
        return TabularData(
            header=[
                attr.title for attr in BlameLine.attributes
                if attr.name in self.columns
            ],
            rows=rows
        )


@analysis(slug='breakdown')
class BreakdownAnalysis(Analysis):
    configuration = [
        configurable.Config(
            param='attributes',
            accessor='breakdown_attributes',
            required=True
        )
    ]

    def __call__(self):
        attributes = [a.name for a in self.attributes]
        return self.count_lines_by_attr(*attributes)

    def get_tabular_data(self):
        def pct_formatter(v):
            num_lines = sum(f.num_lines for f in self.files)
            return "{:.12%}".format((v / num_lines))

        tabulated = tabulate_nested_attribute_data(
            self.result, formatter=pct_formatter)

        return TabularData(
            header=["File Type", "Contributor", "Num Lines", "Contributions"],
            rows=tabulated
        )


@analyses
class Analyses(Slug(
    singular_model=Analysis,
    choices={
        'line_blame': LineBlameAnalysis(),
        'breakdown': BreakdownAnalysis(),
    },
    configuration=[
        configurable.Config(
            param='line_blame_columns',
            required=False,
            default=[p.name for p in BlameLine.attributes]
        ),
        configurable.Config(
            param='breakdown_attributes',
            required=False,
            default=[p.name for p in BlameLine.attributes]
        ),
        configurable.Config(param='output_file', required=False),
        configurable.Config(param='output_dir', default=utils.LazyFn(
            func=pathlib.Path,
            args=[os.getcwd]
        ))
    ]
)):
    def __call__(self):
        for a in self:
            a(self.files)
        if self.should_output:
            self.output()

    @property
    def should_output(self):
        return self.output_dir is not None \
            or self.output_file is not None \
            or self.output_type is not None

    def output(self):
        for a in self:
            a.output()

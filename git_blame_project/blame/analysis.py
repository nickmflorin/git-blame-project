import collections
import csv
import pathlib
import os

from git_blame_project.formatters import path_formatter
from git_blame_project.models import Slug, OutputTypes, OutputType
from git_blame_project.stdout import info, not_supported
from git_blame_project.utils import Callback

from .blame_line import BlameLine
from .git_env import get_git_branch


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


TabularData = collections.namedtuple('TabularData', ['header', 'rows'])


class Analysis(Slug(
    plural_model='git_blame_project.blame.analysis.Analyses',
    configuration=[
        Slug.Config(name='dry_run', default=False),
        Slug.Config(
            name='repository',
            required=True,
            formatter=path_formatter()
        ),
        Slug.Config(name='num_analyses', required=True),
        Slug.Config(name='output_file', required=False),
        Slug.Config(name='output_type', required=False),
        Slug.Config(name='output_dir', default=Callback(
            func=pathlib.Path,
            args=[os.getcwd]
        ))
    ]
)):
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

    @property
    def output_type(self):
        if self.config.output_type is not None:
            return self.config.output_type
        elif self.config.output_file is not None:
            return OutputTypes.from_extensions(self.config.output_file.extension)
        # TODO: Should we return the default?  Or should this represent a case
        # where we do not output?
        return OutputTypes.all()

    def output(self):
        output_mapping = {
            OutputTypes.CSV.slug: self.output_csv,
            OutputTypes.EXCEL.slug: self.output_excel,
        }
        for output_type in self.config.output_type:
            output_mapping[output_type.slug]()

    def default_output_file_name(self, suffix=None):
        branch_name = get_git_branch(self.config.repository)
        if suffix is None and getattr(self, 'output_file_suffix'):
            suffix = self.output_file_suffix
        if suffix is not None:
            return (
                f"{self.config.output_dir.parts[-1]}-{branch_name}-"
                f"{suffix}"
            )
        return f"{self.config.output_dir.parts[-1]}-{branch_name}"

    def default_output_file_path(self, output_type, suffix=None):
        return OutputType.for_slug(output_type) \
            .format_filename(self.default_output_file_name(suffix=suffix))

    def output_file(self, output_type):
        # The output file is guaranteed to be an existing directory or a file
        # that may or may not exist, but in a parent directory that does exist.
        suffix = None

        self.default_output_file_name('csv')
        if self.config.num_analyses > 1:
            if getattr(self, 'output_file_suffix', None):
                suffix = self.output_file_suffix
            else:
                suffix = self.slug
        if self.config.output_file is not None:
            return self.config.output_file.filepath(output_type, suffix=suffix)
        return self.config.output_dir / self.default_output_file_path(
            output_type=output_type,
            suffix=suffix
        )

    def output_csv(self):
        output_file = self.output_file('csv')
        info(f"Writing to {str(output_file)}")

        if not hasattr(self, 'get_tabular_data'):
            raise TypeError(
                f"The analysis class {self.__class__} does not expose a "
                "method for retrieving the tabular data."
            )
        data = self.get_tabular_data()
        if not self.config.dry_run:
            with open(str(output_file), 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(data.header)
                writer.writerows(data.rows)

    def output_excel(self):
        not_supported("The `excel` output type is not yet supported.")


@analysis(slug='line_blame')
class LineBlameAnalysis(Analysis):
    configuration = [
        Slug.Config(
            name='columns',
            plural_name='line_blame_columns',
            default=[p.name for p in BlameLine.attributes]
        )
    ]

    def __call__(self):
        return self.files

    def get_tabular_data(self):
        rows = []
        for file in self.result:
            rows += file.csv_rows(self.config.columns)
        return TabularData(
            header=[
                attr.title for attr in BlameLine.attributes
                if attr.name in self.config.columns
            ],
            rows=rows
        )


@analysis(slug='contributions_by_line')
class ContributionsByLineAnalysis(Analysis):
    def __call__(self):
        return self.count_lines_by_attr(attr='contributor')

    def get_tabular_data(self):
        def pct_formatter(v):
            num_lines = sum(f.num_lines for f in self.files)
            return "{:.12%}".format((v / num_lines))

        return TabularData(
            header=["Contributor", "Contributions"],
            rows=[
                [k, pct_formatter(v)] for k, v in self.result.items()
            ]
        )


@analyses
class Analyses(Slug(
    singular_model=Analysis,
    line_blame=LineBlameAnalysis(),
    contributions_by_line=ContributionsByLineAnalysis(),
    configuration=[
        Slug.Config(
            name='line_blame_columns',
            required=False,
            default=[p.name for p in BlameLine.attributes]
        ),
        Slug.Config(name='output_file', required=False),
        Slug.Config(name='output_dir', default=Callback(
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
        return self.config.output_dir is not None \
            or self.config.output_file is not None \
            or self.config.output_type is not None

    def output(self):
        for a in self:
            a.output()

import collections
import csv
import functools

from git_blame_project.models import SlugModel, OutputTypes, OutputType
from git_blame_project.stdout import info, not_supported

from .blame_line import BlameLine
from .git_env import get_git_branch


def save_result(func):
    @functools.wraps(func)
    def decorated(instance, *args, **kwargs):
        result = func(instance, *args, **kwargs)
        setattr(instance, '_result', result)
        return result
    return decorated


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


def analysis(slug):
    def klass_decorator(cls):
        cls = analyses(cls)
        setattr(cls, 'slug', slug)
        return cls
    return klass_decorator


TabularData = collections.namedtuple('TabularData', ['header', 'rows'])


class Analysis(SlugModel(
        plural_model='git_blame_project.blame.analysis.Analyses')):

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

    def output(self, blame):
        output_mapping = {
            OutputTypes.CSV.slug: self.output_csv,
            OutputTypes.EXCEL.slug: self.output_excel,
        }
        for output_type in blame.output_type:
            output_mapping[output_type.slug](blame)

    def default_output_file_name(self, blame, suffix=None):
        branch_name = get_git_branch(blame.repository)
        if suffix is None and getattr(self, 'output_file_suffix'):
            suffix = self.output_file_suffix
        if suffix is not None:
            return (
                f"{blame.outputdir.parts[-1]}-{branch_name}-"
                f"{suffix}"
            )
        return f"{blame.outputdir.parts[-1]}-{branch_name}"

    def default_output_file_path(self, blame, output_type, suffix=None):
        return OutputType.for_slug(output_type) \
            .format_filename(
                self.default_output_file_name(blame, suffix=suffix))

    def output_file(self, blame, output_type):
        # The output file is guaranteed to be an existing directory or a file
        # that may or may not exist, but in a parent directory that does exist.
        suffix = None
        if len(blame.analyses) > 1:
            if getattr(self, 'output_file_suffix', None):
                suffix = self.output_file_suffix
            else:
                suffix = self.slug
        if blame._output_file is not None:
            return blame._output_file.filepath(output_type, suffix=suffix)
        return blame.outputdir / self.default_output_file_path(
            blame=blame,
            output_type=output_type,
            suffix=suffix
        )

    def output_csv(self, blame):
        output_file = self.output_file(blame, 'csv')
        info(f"Writing to {str(output_file)}")

        if not hasattr(self, 'get_tabular_data'):
            raise TypeError(
                f"The analysis class {self.__class__} does not expose a "
                "method for retrieving the tabular data."
            )
        data = self.get_tabular_data(blame)
        if not blame.dry_run:
            with open(str(output_file), 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(data.header)
                writer.writerows(data.rows)

    def output_excel(self):
        not_supported("The `excel` output type is not yet supported.")


@analysis(slug='line_blame')
class LineBlameAnalysis(Analysis):
    def __call__(self):
        return self.files

    def get_tabular_data(self, blame):
        rows = []
        for file in self.result:
            rows += file.csv_rows(blame.line_blame_columns)
        return TabularData(
            header=[
                attr.title for attr in BlameLine.attributes
                if attr.name in blame.line_blame_columns
            ],
            rows=rows
        )


@analysis(slug='contributions_by_line')
class ContributionsByLineAnalysis(Analysis):
    def __call__(self):
        return self.count_lines_by_attr(attr='contributor')

    def get_tabular_data(self, blame):
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
class Analyses(SlugModel(
    singular_model=Analysis,
    line_blame=LineBlameAnalysis(),
    contributions_by_line=ContributionsByLineAnalysis()
)):
    def __call__(self):
        for a in self:
            a(self.files)

    def output(self, blame):
        for a in self:
            a.output(blame)

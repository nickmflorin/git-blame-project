import click

from git_blame_project import utils
from git_blame_project.blame import BlameLine

from .help import HelpText
from .types import (
    CommaSeparatedListType, OutputFileType, OutputFileDirType, OutputTypeType,
    AnalysisType)


class Option:
    def __init__(self, name, help_text="", **kwargs):
        self.name = name
        self.help_text = help_text
        self.kwargs = kwargs

    def __call__(self, func):
        return click.option(
            f"--{self.name}",
            help=self.help_text,
            **self.kwargs
        )(func)


class Options(utils.ImmutableSequence):
    def __call__(self, func):
        for option in self:
            func = option(func)
        return func


options = Options(
    Option('file_limit', type=int, help_text=HelpText.FILE_LIMIT),
    Option('dry_run', is_flag=True, default=False),
    Option('analyses', type=AnalysisType(), help_text=HelpText.ANALYSIS),
    Option('output_type', type=OutputTypeType(), help_text=HelpText.OUTPUT_TYPE),
    Option('output_file', type=OutputFileType(), help_text=HelpText.OUTPUT_FILE),
    Option(
        name='output_dir',
        type=OutputFileDirType(exists=True),
        help_text=HelpText.OUTPUT_DIR
    ),
    Option(
        name='ignore_dirs',
        type=CommaSeparatedListType(),
        help_text=HelpText.IGNORE_DIRS
    ),
    Option(
        'ignore_file_types',
        type=CommaSeparatedListType(),
        help_text=HelpText.IGNORE_FILE_TYPES
    ),
    Option(
        name='line_blame_columns',
        help_text=HelpText.LINE_BLAME_COLUMS,
        type=CommaSeparatedListType(
            choices=[p.name for p in BlameLine.attributes]
        )
    )
)

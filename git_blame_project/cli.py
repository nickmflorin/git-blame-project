import sys

import click

import git_blame_project
from git_blame_project.blame.analysis import LineBlameAnalysis

from .blame import Analyses, Blame, BlameLine
from .constants import HelpText
from .types import (
    RootParamType, CommaSeparatedListType, OutputFileType, OutputFileDirType,
    OutputTypeType, AnalysisType)


def welcome_message():
    message = (
        f"Welcome to {git_blame_project.__appname__}!\n"
        f"{git_blame_project.__copyright__}\n"
        "All Rights Reserved\n\n"
    )
    sys.stdout.write(message)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
@click.option('--file_limit', type=int, help=HelpText.FILE_LIMIT)
@click.option('--dry_run', is_flag=True, default=False, help="")
@click.option('--analyses', type=AnalysisType(), help=HelpText.ANALYSIS)
@click.option('--output_type', type=OutputTypeType(), help=HelpText.OUTPUT_TYPE)
@click.option('--output_file', type=OutputFileType(), help=HelpText.OUTPUT_FILE)
@click.option(
    '--output_dir',
    type=OutputFileDirType(exists=True),
    help=HelpText.OUTPUT_DIR
)
@click.option(
    '--ignore_dirs',
    type=CommaSeparatedListType(),
    help=HelpText.IGNORE_DIRS
)
@click.option(
    '--ignore_file_types',
    type=CommaSeparatedListType(),
    help=HelpText.IGNORE_FILE_TYPES
)
@click.option('--line_blame_columns', type=CommaSeparatedListType(
    choices=[p.name for p in BlameLine.attributes]
), help=HelpText.LINE_BLAME_COLUMS)
def main(repository, **kwargs):
    welcome_message()

    kwargs.setdefault('analyses', Analyses(LineBlameAnalysis()))
    kwargs['analyses'] = kwargs['analyses'].to_dynamic(config={
        'repository': repository,
        'line_blame_columns': kwargs.pop('line_blame_columns'),
        'output_dir': kwargs.pop('output_dir'),
        'output_file': kwargs.pop('output_file'),
        'output_type': kwargs.pop('output_type'),
        'dry_run': kwargs.pop('dry_run'),
        'num_analyses': len(kwargs['analyses'])
    })
    blamed = Blame(repository, **kwargs)
    blamed()

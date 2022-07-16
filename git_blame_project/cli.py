import sys

import click

import git_blame_project

from .constants import HelpText
from .blame import Blame, BlameLine
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
@click.option('--file_limit', '-fl', type=int, help=HelpText.FILE_LIMIT)
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
    blamed = Blame(repository, **kwargs)
    blamed()

import sys

import click

import git_blame_project

from .constants import HelpText
from .models import Blame, BlameLine
from .types import (
    RootParamType, CommaSeparatedListType, OutputFileType, OutputFileDirType,
    OutputTypeType)


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
@click.option('--filelimit', '-fl', type=int, help=HelpText.FILE_LIMIT)
@click.option('--outputtype', type=OutputTypeType(), help=HelpText.OUTPUT_TYPE)
@click.option('--outputfile', type=OutputFileType(), help="")
@click.option('--outputdir', type=OutputFileDirType(exists=True), help="")
@click.option('--outputcols', type=CommaSeparatedListType(
    choices=[p.name for p in BlameLine.parse_attributes]
), help=HelpText.OUTPUT_COLS)
def main(repository, **kwargs):
    welcome_message()
    blamed = Blame(
        repository,
        ignore_dirs=["migrations", ".git"],
        ignore_file_types=[
            "woff", "woff2", "eot", "ttf", "svg", ".lock", ".json"],
        **kwargs
    )
    blamed()
    results = blamed.get_contributions_by_line()
    blamed.output()
    print(results)

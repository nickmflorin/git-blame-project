import sys
import click

import git_blame_project
from git_blame_project.blame import LineBlameAnalysis, BreakdownAnalysis

from .options import blame_lines_options, options
from .types import RootParamType, BreakdownAttributeType


def welcome_message():
    message = (
        f"\nWelcome to {git_blame_project.__appname__}!\n"
        f"{git_blame_project.__copyright__}\n"
        "All Rights Reserved\n\n"
    )
    sys.stdout.write(message)


@click.group()
@click.pass_context
def cli(ctx):
    welcome_message()


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
@blame_lines_options
def blame_lines(repository, **kwargs):
    analysis = LineBlameAnalysis(config=dict(repository=repository, **kwargs))
    analysis()


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
@click.argument(
    'attributes',
    type=BreakdownAttributeType(),
)
@options
def breakdown(repository, **kwargs):
    analysis = BreakdownAnalysis(config=dict(repository=repository, **kwargs))
    analysis()

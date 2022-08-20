import sys
import click

import git_blame_project
from git_blame_project.blame import Analyses, Blame

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
    kwargs['analyses'] = Analyses('line_blame')
    kwargs['analyses'].to_dynamic(config={
        'repository': repository,
        'line_blame_columns': kwargs.pop('columns'),
        'output_dir': kwargs.pop('output_dir'),
        'output_file': kwargs.pop('output_file'),
        'output_type': kwargs.pop('output_type'),
        'dry_run': kwargs.pop('dry_run'),
        'num_analyses': 1,
    })
    blamed = Blame(repository, config=kwargs)
    blamed()


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
@click.argument(
    'attributes',
    type=BreakdownAttributeType(),
)
@options
def breakdown(repository, **kwargs):
    kwargs['analyses'] = Analyses('breakdown')
    kwargs['analyses'].to_dynamic(config={
        'repository': repository,
        'breakdown_attributes': kwargs.pop('attributes'),
        'output_dir': kwargs.pop('output_dir'),
        'output_file': kwargs.pop('output_file'),
        'output_type': kwargs.pop('output_type'),
        'dry_run': kwargs.pop('dry_run'),
        'num_analyses': 1,
    })
    blamed = Blame(repository, config=kwargs)
    blamed()

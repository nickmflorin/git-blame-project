import sys
import click

import git_blame_project
from git_blame_project import utils, configurable, models, exceptions
from git_blame_project.blame import Analyses, Blame
from git_blame_project.blame.analysis import LineBlameAnalysis
from git_blame_project import models

from .options import options
from .types import RootParamType


def welcome_message():
    message = (
        f"\nWelcome to {git_blame_project.__appname__}!\n"
        f"{git_blame_project.__copyright__}\n"
        "All Rights Reserved\n\n"
    )
    sys.stdout.write(message)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
@options
def main(repository, **kwargs):
    welcome_message()

    kwargs.setdefault('analyses', Analyses('line_blame'))

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

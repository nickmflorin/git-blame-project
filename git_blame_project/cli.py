import sys

import click

import git_blame_project

from .models import Blame
from .types import RootParamType


DIRECTORY = "/Users/nick/repos/happybudget"

DEFAULT_IGNORE_DIRECTORIES = ['.git', 'node_modules', 'svgs']


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


# class BasedIntParamType(click.ParamType):
#     name = "integer"

#     def convert(self, value, param, ctx):
#         if isinstance(value, int):
#             return value

#         try:
#             if value[:2].lower() == "0x":
#                 return int(value[2:], 16)
#             elif value[:1] == "0":
#                 return int(value, 8)
#             return int(value, 10)
#         except ValueError:
#             self.fail(f"{value!r} is not a valid integer", param, ctx)


@cli.command()
@click.argument('repository', type=RootParamType(exists=True))
def main(repository):
    welcome_message()
    blamed = Blame(
        repository,
        ignore_dirs=["migrations", ".git"],
        ignore_file_types=[
            "woff", "woff2", "eot", "ttf", "svg", ".lock", ".json"]
    )
    blamed()
    blamed.analyze_contributors()

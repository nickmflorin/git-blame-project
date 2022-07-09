import os
import re
import subprocess
import pathlib

import click

# from .dateutils import ensure_datetime


DIRECTORY = "/Users/nick/repos/happybudget-api"

DEFAULT_IGNORE_DIRECTORIES = ['.git']


COMMIT_REGEX = r"([\^a-zA-Z0-9]*)"
DATE_REGEX = r"([0-9]{4})-([0-9]{2})-([0-9]{2})"
TIME_REGEX = r"([0-9]{2}):([0-9]{2}):([0-9]{2})"

REGEX_STRING = COMMIT_REGEX \
    + r"\s*\(([a-zA-Z0-9\s]*)\s*" \
    + DATE_REGEX + r"\s*" \
    + TIME_REGEX + r"\s*" \
    + r"([-0-9]*)\s*([-0-9]*)\)\s*(.*)"


import datetime
from dateutil import parser


def ensure_datetime(value):
    """
    Ensures that the provided value is a `obj:datetime.datetime` instance
    by either converting a `obj:str` to a `obj:datetime.datetime` instance
    or a `obj:datetime.date` instance to a `obj:datetime.datetime` instance.
    If the value cannot be safely converted to a `obj:datetime.datetime`
    instance, a ValueError will be raised.
    Args:
        value (`obj:datetime.datetime`, `obj:datetime.date` or `obj:str)
            The value that should be converted to a `obj:datetime.datetime`
            instance.
    """
    if type(value) is datetime.datetime:
        return value
    elif type(value) is datetime.date:
        return datetime.datetime.combine(value, datetime.datetime.min.time())
    elif isinstance(value, str):
        try:
            return parser.parse(value)
        except ValueError as e:
            raise ValueError(
                "The provided value cannot be converted to a "
                "datetime.datetime instance."
            ) from e
    else:
        raise ValueError(
            "Invalid value %s supplied - cannot convert to datetime." % value)


def datetime_obj(groups):
    datetime_string = f"{groups[2]}-{groups[3]}-{groups[4]} " \
        + f"{groups[5]}:{groups[6]}:{groups[7]}"
    # TODO: Handle errors!
    return ensure_datetime(datetime_string)


class FailedBlameLine:
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data


class BlameLine:
    def __init__(self, code, commit, collaborator, dt, line_no):
        self._code = code
        self._commit = commit
        self._collaborator = collaborator
        self._dt = dt
        self._line_no = line_no

    @classmethod
    def create(cls, data):
        # cc55be13 (nickmflorin 2021-02-27 13:56:47 -0500  1) [tox]
        if data.strip() == "":
            return None
        result = re.search(REGEX_STRING, data)
        if result is None:
            return FailedBlameLine(data=data)
        groups = result.groups()
        try:
            return BlameLine(
                commit=groups[0],
                collaborator=groups[1],
                dt=datetime_obj(groups),
                line_no=groups[9],
                code=groups[10]
            )
        except IndexError:
            return FailedBlameLine(data=data)


class FailedBlameFile:
    def __init__(self, path, name, error):
        self._path = path
        self._error = error
        self._name = name

    @property
    def full_name(self):
        return "%s" % (self._path / self._name)


class BlameFile:
    def __init__(self, blame_lines):
        self._blame_lines = blame_lines

    @classmethod
    def create(cls, path, name):
        pt = pathlib.Path(path)
        if any([p in DEFAULT_IGNORE_DIRECTORIES for p in pt.parts]):
            return None
        try:
            result = subprocess.check_output(
                ['git', 'blame', os.path.join(path, name)])
        except subprocess.CalledProcessError as error:
            print(error)
            return FailedBlameFile(path=pt, name=name, error=error)
        else:
            try:
                result = result.decode("utf-8")
            except UnicodeDecodeError as error:
                return FailedBlameFile(path=pt, name=name, error=error)

            blame_lines = []
            for raw_line in result.split("\n"):
                blamed = BlameLine.create(raw_line)
                if blamed is None:
                    continue
                elif isinstance(blamed, FailedBlameLine):
                    print("Could not parse line %s." % blamed.data)
                else:
                    print(blamed._code)
                    blame_lines.append(blamed)
            return cls(blame_lines)


@click.command()
def blame():
    blamed = []
    os.chdir(DIRECTORY)
    for path, _, files in os.walk(DIRECTORY):
        for name in files:
            blamed_file = BlameFile.create(path, name)
            if isinstance(blamed_file, FailedBlameFile):
                print("Could not parse file %s." % blamed_file.full_name)
            else:
                blamed.append(blamed_file)

if __name__ == '__main__':
    blame()

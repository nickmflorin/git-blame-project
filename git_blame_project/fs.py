import contextlib
import os


@contextlib.contextmanager
def repository_directory_context(repository):
    original_dir = os.getcwd()
    try:
        os.chdir(str(repository))
        yield None
    finally:
        os.chdir(original_dir)

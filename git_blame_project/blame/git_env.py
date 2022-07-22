import contextlib
import os
import pathlib
import subprocess

from git_blame_project import stdout, utils


@contextlib.contextmanager
def repository_directory_context(repository):
    original_dir = os.getcwd()
    try:
        os.chdir(str(repository))
        yield None
    finally:
        os.chdir(original_dir)


def get_git_branch(repository):
    with repository_directory_context(repository):
        result = subprocess.check_output(['git', 'branch'])
        try:
            result = result.decode("utf-8")
        except UnicodeDecodeError:
            stdout.warning(
                "There was an error determining the current git branch for "
                "purposes of auto-generating a filename.  A placeholder value "
                "will be used."
            )
            return "unknown"
        lines = [r.strip() for r in result.split("\n")]
        for line in lines:
            if line.startswith("*"):
                return line.split("*")[1].strip()
        stdout.warning(
            "There was an error determining the current git branch for "
            "purposes of auto-generating a filename.  A placeholder value "
            "will be used."
        )
        return "unknown"


class LocationContext:
    attrs = ["repository", "repository_path", "file_name"]

    def __init__(self, **kwargs):
        if 'context' in kwargs:
            if not isinstance(kwargs['context'], LocationContext):
                raise ValueError(
                    "The provided context must be an instance of "
                    f"{LocationContext}."
                )
            self._repository = kwargs['context'].repository
            self._repository_path = kwargs['context'].repository_path
            self._file_name = kwargs['context'].file_name
        else:
            missing_kwargs = [a for a in self.attrs if a not in kwargs]
            if missing_kwargs:
                if len(missing_kwargs) == 1:
                    raise TypeError(
                        f"The parameter `{missing_kwargs[0]}` is required.")
                else:
                    humanized = utils.humanize_list(
                        [f"`{a}`" for a in missing_kwargs])
                    raise ValueError(f"The parameters {humanized} are required.")

            self._repository = kwargs['repository']
            self._repository_path = kwargs['repository_path']
            self._file_name = kwargs['file_name']

    def __str__(self):
        return self.full_name

    @property
    def file_name(self):
        return self._file_name

    @property
    def repository(self):
        if not isinstance(self._repository, pathlib.Path):
            return pathlib.Path(self._repository)
        return self._repository

    @property
    def repository_path(self):
        if not isinstance(self._repository_path, pathlib.Path):
            return pathlib.Path(self._repository_path)
        return self._repository_path

    @property
    def absolute_path(self):
        return self.repository / self.repository_path

    @property
    def absolute_file_path(self):
        return self.absolute_path / self.file_name

    @property
    def repository_file_path(self):
        return self.repository_path / self.file_name

    @property
    def absolute_name(self):
        return "%s" % self.absolute_file_path

    @property
    def repository_name(self):
        return "%s" % self.repository_file_path


class LocationContextExtensible(LocationContext):
    @property
    def context(self):
        return LocationContext(
            repository=self._repository,
            repository_path=self._repository_path,
            file_name=self._file_name
        )

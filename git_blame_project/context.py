import pathlib

from git_blame_project.utils import humanize_list


class LocationContext:
    attrs = ["repository", "repository_path", "name"]

    def __init__(self, **kwargs):
        if 'context' in kwargs:
            if not isinstance(kwargs['context'], LocationContext):
                raise ValueError(
                    "The provided context must be an instance of "
                    f"{LocationContext}."
                )
            self._repository = kwargs['context'].repository
            self._repository_path = kwargs['context'].repository_path
            self._name = kwargs['context'].name
        else:
            missing_kwargs = [a for a in self.attrs if a not in kwargs]
            if missing_kwargs:
                humanized = humanize_list(missing_kwargs)
                raise ValueError(f"The parameters {humanized} are required.")

            self._repository = kwargs['repository']
            self._repository_path = kwargs['repository_path']
            self._name = kwargs['name']

    def __str__(self):
        return self.full_name

    @property
    def name(self):
        return self._name

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
        return self.absolute_path / self.name

    @property
    def repository_file_path(self):
        return self.repository_path / self.name

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
            name=self._name
        )

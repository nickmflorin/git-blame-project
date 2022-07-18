import pathlib


def path_formatter():
    def _formatter(value):
        if not isinstance(value, pathlib.Path):
            return pathlib.Path(value)
        return value
    return _formatter

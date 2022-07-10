import pathlib
import click


class PathType(click.Path):
    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if value is not None:
            return pathlib.Path(value)
        return value


class RootParamType(PathType):
    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        gitdir = value / ".git"
        if not gitdir.exists():
            self.fail(
                f"{str(value)!r} does not appear to be a git repository.",
                param,
                ctx
            )
        return value

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


class CommaSeparatedListType(click.types.StringParamType):
    def __init__(self, *args, **kwargs):
        self._choices = kwargs.pop('choices', None)
        self._case_sensitive = kwargs.pop('case_sensitive', False)
        super().__init__(*args, **kwargs)

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)

        results = [a.strip() for a in value.split(',')]
        if self._choices is not None:
            validated = []
            choices_type = click.types.Choice(
                self._choices,
                self._case_sensitive
            )
            for result in results:
                validated.append(choices_type.convert(result, param, ctx))
            return validated
        return results

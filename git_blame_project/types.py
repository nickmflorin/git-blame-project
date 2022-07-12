import pathlib
import click

from git_blame_project.utils import humanize_list

from .stdout import inconsistent_output_location_warning


VALID_OUTPUT_FILE_TYPES = ["csv", "xlsx"]


class PathType(click.Path):
    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        return pathlib.Path(value)


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


class DirectoryType(PathType):
    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if value.exists():
            if not value.is_dir():
                self.fail(
                    f"The path {str(value)} is not a directory.",
                    param,
                    ctx
                )
        elif value.suffix != "":
            self.fail(
                f"The path {str(value)} is not a directory.",
                param,
                ctx
            )
        return value


class OutputFileDirType(DirectoryType):
    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        # The outputfile will not be in the context params if it was either
        # (1) Not provided as a CLI argument.
        # (2) Provided as a CLI argument after the `outputfile` argument.
        # This means that in order to issue warnings against potentially
        # conflicting values of `outputfile` and `outputdir`, we need to perform
        # the checks in both extensions of :obj:`click.params.ParamType` classes
        # (associated with each CLI argument) - because the other parameter
        # will only exist in the context params for one of the
        # :obj:`click.params.ParamType` classes, depending on the order of the
        # parameters as they are included as CLI arguments.
        if 'outputfile' in ctx.params:
            # The output file may either be a directory or a file.  If provided
            # as a directory, it is guaranteed to exist, and if provided as a
            # file, the parent directory is guaranteed to exist - due to checks
            # performed in the OutputFileType.
            outputfile = ctx.params['outputfile']
            if outputfile.is_dir():
                if outputfile != value:
                    inconsistent_output_location_warning(value, outputfile)
            elif outputfile.parent != value:
                inconsistent_output_location_warning(value, outputfile)
        return value


class OutputFileType(PathType):
    def __init__(self, *args, **kwargs):
        # We do not need to ensure that the full path exists in the case that
        # the path includes the filename.  We just need to ensure the directory
        # that the filename is located in exists.
        kwargs.setdefault('exists', False)
        super().__init__(*args, **kwargs)

    def validate_extension(self, ext, param, ctx):
        # TODO: We might want to use the click.types.Choice class here.
        if ext.lower() not in [
                f".{a.lower()}" for a in VALID_OUTPUT_FILE_TYPES]:
            humanized = humanize_list(
                value=VALID_OUTPUT_FILE_TYPES,
                conjunction="or"
            )
            self.fail(
                f"The extension {ext.lower()} is not a supported "
                "output file type.  Output files must be of type "
                f"{humanized}.",
                param,
                ctx
            )

    def convert(self, value, param, ctx):
        # In the case the value is not specified, it will be auto generated
        # based on the repository and the commit.  This will happen after the
        # CLI arguments are collected.
        value = super().convert(value, param, ctx)

        # The determination of whether or not the path refers to a file can
        # only be made if the file exists at that path.
        if value.exists():
            # We do not have to validate whether or not the directory exists
            # because in the case that the value is a file, it can only exist
            # if the parent directory exists.
            if value.is_file():
                self.validate_extension(value.suffix, param, ctx)

        # If the path (as a directory or a filepath) does not exist, we only
        # want to validate the extension in the case that the path refers to
        # a filepath and has an extension - in which case it is not a directory.
        elif value.suffix != "":
            self.validate_extension(value.suffix, param, ctx)
        else:
            # Here, we know that there is not a suffix (which means we are
            # dealing with a directory) and we know that the directory does not
            # exist.  In this case, the value is invalid because we cannot
            # autogenerate a filename and save it in a non-existent parent
            # directory.
            self.fail(
                f"The directory {str(value)} does not exist.",
                param,
                ctx
            )

        # The outputdir will not be in the context params if it was either
        # (1) Not provided as a CLI argument.
        # (2) Provided as a CLI argument after the `outputfile` argument.
        # This means that in order to issue warnings against potentially
        # conflicting values of `outputfile` and `outputdir`, we need to perform
        # the checks in both extensions of :obj:`click.params.ParamType` classes
        # (associated with each CLI argument) - because the other parameter
        # will only exist in the context params for one of the
        # :obj:`click.params.ParamType` classes, depending on the order of the
        # parameters as they are included as CLI arguments.
        if 'outputdir' in ctx.params:
            # The output directory is guaranteed to be a directory that exists.
            outputdir = ctx.params['outputdir']
            assert outputdir.is_dir() and outputdir.exists()
            # if outputdir
            # if outputfile.is_dir():
            #     if outputfile != value:
            #         inconsistent_output_location_warning(value, outputfile)
            # elif outputfile.parent != value:
            #     inconsistent_output_location_warning(value, outputfile)

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

import pathlib
import click

from .constants import OutputTypes
from .stdout import inconsistent_output_location_warning


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


def pathlib_ext(path):
    if path.exists():
        if path.is_file():
            return path.suffix
    elif path.suffix != "":
        return path.suffix
    return None


class OutputFileType(PathType):
    def __init__(self, *args, **kwargs):
        # We do not need to ensure that the full path exists in the case that
        # the path includes the filename.  We just need to ensure the directory
        # that the filename is located in exists.
        kwargs.setdefault('exists', False)
        super().__init__(*args, **kwargs)

    def validate_extension(self, ext, param, ctx):
        # The outputtype will only not be in the context params if it was not
        # specified or specified after the outputfile argument.  If it was
        # specified after the outputfile argument, this validation must be
        # done inside of the outputtype associated extension of
        # :obj:`click.params.ParamType`.
        if 'outputtype' in ctx.params:
            ctx.params['outputtype'].validate_file_extension(ext, ctx, param)
        else:
            OutputTypes.validate_general_file_extension(ext, ctx, param)

    def convert(self, value, param, ctx):
        # In the case the value is not specified, it will be auto generated
        # based on the repository and the commit.  This will happen after the
        # CLI arguments are collected.
        value = super().convert(value, param, ctx)

        # The determination of whether or not the path refers to a file or a
        # directory can only be made if the file exists at that path.
        if value.exists():
            # If the provided value refers to a file that exists, we have to
            # validate the extension.  If the value refers to a directory,
            # we do not have to validate that the directory exists because
            # the directory is guaranteed to exist if the file exists.
            if value.is_file():
                self.validate_extension(value.suffix, param, ctx)

        # If the path (as a directory or a filepath) does not exist, we only
        # want to validate the extension in the case that the path refers to
        # a filepath and has an extension.  If the suffix is an empty string,
        # that means that the path refers to a directory that does not exist.
        elif value.suffix != "":
            self.validate_extension(value.suffix, param, ctx)
        else:
            # TODO: Figure out how to make it so that when output types are
            # provided, the extension isn't required on a file and it can be
            # just a name.
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
            if value.is_dir():
                if value != outputdir:
                    inconsistent_output_location_warning(outputdir, value)
            elif value.parent != outputdir:
                inconsistent_output_location_warning(outputdir, value)
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


class OutputTypeType(CommaSeparatedListType):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            choices=[ot.slug for ot in OutputTypes.__ALL__],
            case_sensitive=False
        )
        super().__init__(*args, **kwargs)

    def convert(self, value, param, ctx):
        validated_choices = super().convert(value, param, ctx)
        output_types = OutputTypes(*validated_choices)
        # The outputfile will only not be in the context params if it was not
        # specified or specified after the outputtype argument.  If it was
        # specified after the outputtype argument, this validation must be
        # done inside of the outputfile associated extension of
        # :obj:`click.params.ParamType`.
        if 'outputfile' in ctx.params:
            if ctx.params['outputfile'].exists():
                if ctx.params['outputfile'].is_file():
                    output_types.validate_file_extension(
                        ctx.params['outputfile'].suffix, ctx, param)
            elif ctx.params['outputfile'].suffix != "":
                output_types.validate_file_extension(
                    ctx.params['outputfile'].suffix, ctx, param)
        return output_types

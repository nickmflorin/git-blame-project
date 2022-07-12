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


class OutputFile:
    def __init__(self, path, raw_value, infer_ext_from_output_type=False):
        self._path = path
        self._raw_value = raw_value
        self._infer_ext_from_output_type = infer_ext_from_output_type


class OutputFileType(PathType):
    INFER_FROM_OUTPUT_TYPE = "INFER_FROM_OUTPUT_TYPE"

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

    def convert(self, v, param, ctx):
        # In the case the value is not specified, it will be auto generated
        # based on the repository and the commit.  This will happen after the
        # CLI arguments are collected.
        raw_value = v
        path_value = super().convert(v, param, ctx)

        # The determination of whether or not the path refers to a file or a
        # directory can only be made if the file exists at that path.
        if path_value.exists():
            # If the provided value refers to a file that exists, we have to
            # validate the extension.  Otherwise, a BadParameter exception
            # should be raised because the path does not point to a file.
            if path_value.is_file():
                # At this point, the extension may be an empty string - but
                # unlike the case where the file does not exist, we need to
                # raise a BadParameter exception in the case that this is true.
                # In the case where the file does not exist, we can try to
                # infer the extension based on the output types.  But in this
                # case, the user is trying to reference an already generated
                # output file that does not have an extension.
                self.validate_extension(path_value.suffix, param, ctx)
                value = OutputFile(
                    path=path_value,
                    raw_value=raw_value
                )
            else:
                self.fail(
                    f"The provided value {str(path_value)} is a directory.",
                    param,
                    ctx
                )
        # If the path does not exist, only validate the extension in the case
        # that there is an extension.  Otherwise, we will try to infer the
        # extension based on the output types.
        elif path_value.suffix != "":
            self.validate_extension(path_value.suffix, param, ctx)
            value = OutputFile(
                path=path_value,
                raw_value=raw_value
            )
        else:
            # Here, the extension will be inferred based on the output types
            # provided.
            value = OutputFile(
                path=path_value,
                raw_value=raw_value,
                infer_ext_from_output_type=True
            )

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

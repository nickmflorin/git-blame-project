import pathlib
import click

from git_blame_project import utils
from git_blame_project.blame import BlameLine
from git_blame_project.models import OutputFile, OutputTypes


def inconsistent_output_location_warning(output_dir, outputfile):
    utils.stdout.warning(
        f"The output directory {str(output_dir)} is inconsistent "
        f"with the location of the provided output file, "
        f"{str(outputfile)}.  Remember, only one of the output "
        "file or the output directory are used. \n"
        f"The provided output directory {str(output_dir)} will be "
        "ignored as the location defined by the output file "
        "will be used."
    )


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
        # conflicting values of `outputfile` and `output_dir`, we need to perform
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
        raw_value = value
        path_value = super().convert(value, param, ctx)

        outputfile = OutputFile(path=path_value, raw_value=raw_value)

        # The determination of whether or not the path refers to a file or a
        # directory can only be made if the file exists at that path.
        if outputfile.path.exists():
            # If the provided value refers to a file that exists, we have to
            # validate the extension.  Otherwise, a BadParameter exception
            # should be raised because the path does not point to a file.
            if outputfile.path.is_file():
                # At this point, the extension may be an empty string - but
                # unlike the case where the file does not exist, we need to
                # raise a BadParameter exception in the case that this is true.
                # In the case where the file does not exist, we can try to
                # infer the extension based on the output types.  But in this
                # case, the user is trying to reference an already generated
                # output file that does not have an extension.
                self.validate_extension(outputfile.extension, param, ctx)
            else:
                self.fail(
                    f"The provided value {str(outputfile)} is a directory.",
                    param,
                    ctx
                )
        # If the path does not exist, only validate the extension in the case
        # that there is an extension.  Otherwise, we will try to infer the
        # extension based on the output types.
        elif outputfile.extension != "":
            self.validate_extension(outputfile.extension, param, ctx)

        if not outputfile.directory.exists():
            self.fail(
                f"The provided value {str(outputfile)} is in a "
                f"directory {str(outputfile.directory)} that does "
                "not exist."
            )

        # The output_dir will not be in the context params if it was either
        # (1) Not provided as a CLI argument.
        # (2) Provided as a CLI argument after the `outputfile` argument.
        # This means that in order to issue warnings against potentially
        # conflicting values of `outputfile` and `output_dir`, we need to perform
        # the checks in both extensions of :obj:`click.params.ParamType` classes
        # (associated with each CLI argument) - because the other parameter
        # will only exist in the context params for one of the
        # :obj:`click.params.ParamType` classes, depending on the order of the
        # parameters as they are included as CLI arguments.
        if 'output_dir' in ctx.params:
            # The output directory is guaranteed to be a directory that exists.
            output_dir = ctx.params['output_dir']
            assert output_dir.is_dir() and output_dir.exists(), \
                "The output directory should be validated as a valid " \
                "directory that exists."
            if outputfile.directory != output_dir:
                inconsistent_output_location_warning(output_dir, outputfile)
        return outputfile


class CommaSeparatedListType(click.types.StringParamType):
    choices = None

    def __init__(self, *args, **kwargs):
        self._choices = kwargs.pop('choices', self.choices)
        self._case_sensitive = kwargs.pop('case_sensitive', False)
        self._choices_type = click.types.Choice(
            self._choices,
            self._case_sensitive
        )
        super().__init__(*args, **kwargs)

    def convert_value(self, value, param=None, ctx=None):
        value = value.strip()
        if self._choices is not None:
            return self._choices_type.convert(value, param, ctx)
        return value

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        results = set([a.strip() for a in value.split(',')])
        if self._choices is not None:
            return [self.convert_value(v, param, ctx) for v in results]
        return results


class BreakdownAttributeType(CommaSeparatedListType):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            choices=[attr.name for attr in BlameLine.attributes],
            case_sensitive=False
        )
        super().__init__(*args, **kwargs)

    def convert(self, value, param, ctx):
        validated_choices = super().convert(value, param, ctx)
        return [BlameLine.get_attribute(a) for a in validated_choices]


class MultipleSlugType(CommaSeparatedListType):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            choices=[option.slug for option in self.plural_slug_cls.__ALL__],
            case_sensitive=False
        )
        super().__init__(*args, **kwargs)

    def convert(self, value, param, ctx):
        validated_choices = super().convert(value, param, ctx)
        return self.plural_slug_cls(*validated_choices)

    @property
    def plural_slug_cls(self):
        raise NotImplementedError()


class OutputTypeType(MultipleSlugType):
    plural_slug_cls = OutputTypes

    def convert(self, value, param, ctx):
        output_types = super().convert(value, param, ctx)
        # The outputfile will only not be in the context params if it was not
        # specified or specified after the outputtype argument.  If it was
        # specified after the outputtype argument, this validation must be
        # done inside of the outputfile associated extension of
        # :obj:`click.params.ParamType`.
        if 'outputfile' in ctx.params:
            outputfile = ctx.params['outputfile']
            # The extension will be an empty string if we are inferring the
            # extension based on the output types.
            if outputfile.extension != "":
                output_types.validate_file_extension(outputfile.path, ctx, param)
        return output_types

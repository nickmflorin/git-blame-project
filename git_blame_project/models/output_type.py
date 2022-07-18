import pathlib
from click.exceptions import BadParameter

from git_blame_project.stdout import warning, TerminalCodes
from git_blame_project.utils import (
    iterable_from_args, humanize_list, standardize_extension,
    standardize_extensions, extensions_equal)

from .slug import Slug


class OutputType(Slug(plural_model='git_blame_project.models.OutputTypes')):
    def __init__(self, slug, ext):
        super().__init__(slug)
        self._ext = ext

    @property
    def ext(self):
        return standardize_extension(self._ext)

    @classmethod
    def get_extension(cls, slug):
        return cls.get_for_slug(slug).ext

    def format_filename(self, filename):
        if not isinstance(filename, pathlib.Path):
            filename = pathlib.Path(filename)
        return filename.with_suffix(self.ext)


class OutputTypes(Slug(
    singular_model=OutputType,
    csv={'slug': 'csv', 'ext': 'csv'},
    excel={'slug': 'excel', 'ext': 'xlsx'},
    cumulative=lambda __ALL__: {
        'valid_extensions': set(
            standardize_extensions([ot.ext for ot in __ALL__]))
    }
)):
    @classmethod
    def from_extensions(cls, *exts):
        # A single extension can be associated with multiple OutputTypes, so
        # we have to return all of them.
        extensions = iterable_from_args(*exts)
        output_types = []
        for ext in extensions:
            ots = [
                ot for ot in OutputTypes.__ALL__
                if extensions_equal(ext, ot.ext)
            ]
            output_types += ots
        return cls(output_types)

    def get_extensions(self, include_prefix=True):
        return standardize_extensions(
            [ot.ext for ot in self],
            include_prefix=include_prefix
        )

    @classmethod
    def validate_general_file_extension(cls, ext, ctx, param):
        if standardize_extension(ext) not in cls.VALID_EXTENSIONS:
            humanized = humanize_list(cls.VALID_EXTENSIONS, conjunction="or")
            if ext.strip() == "":
                raise BadParameter(
                    f"The file is missing an extension.  Output files must "
                    f"be of type {humanized}.",
                    ctx=ctx,
                    param=param
                )
            raise BadParameter(
                f"The extension {ext.lower()} is not a supported "
                "output file type.  Output files must be of type "
                f"{humanized}.",
                ctx=ctx,
                param=param
            )

    def validate_file_extension(self, ext, ctx, param):
        if isinstance(ext, pathlib.Path):
            ext = ext.suffix

        self.validate_general_file_extension(ext, ctx, param)
        humanized = humanize_list(
            value=[TerminalCodes.bold(s) for s in self.slugs],
            conjunction="and"
        )
        humanized_extensions = humanize_list(
            value=[TerminalCodes.bold(ext) for ext in self.get_extensions()],
            conjunction="and"
        )
        ext = standardize_extension(ext)
        extensions = self.get_extensions()
        if len(self) > 1 and ext not in extensions:
            # In the case that we are using multiple output types, the
            # filenames will be generated with extensions corresponding to
            # those output types.  In this case, if the provided filename
            # has an inconsistent extension, just let the user know that it
            # will be ignored.  Generally, when providing the output types,
            # the file extension is not required and just the name of the
            # file can be provided.
            warning(
                "The file extension is inconsistent with the provided "
                f"output types {humanized}, which will generate files with "
                f"extensions {humanized_extensions}."
                "The extension on the provided file type, "
                f"{TerminalCodes.bold(ext)}, will be ignored, but the filename "
                "will still be used. \n"
                "Note: If providing the output types explicitly, it is "
                "okay to omit the extension from the filename."
            )
        elif ext not in extensions:
            outputtype = self[0]
            warning(
                "The file extension is inconsistent with the provided "
                f"output type {TerminalCodes.bold(outputtype.slug)}, which "
                f"will generate a file with extension "
                f"{TerminalCodes.bold(outputtype.ext)}. "
                "The extension on the provided file type, "
                f"{TerminalCodes.bold(ext)}, and the output file will be used "
                "with the correct extension, "
                f"{TerminalCodes.bold(outputtype.ext)}.\n"
                "Note: If providing the output types explicitly, it is "
                "okay to omit the extension from the filename."
            )

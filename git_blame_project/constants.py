from click.exceptions import BadParameter

from git_blame_project.utils import humanize_list, ImmutableSequence
from .stdout import warning, TerminalCodes


DEFAULT_IGNORE_DIRECTORIES = ['.git']
DEFAULT_IGNORE_FILE_TYPES = [".png", ".jpeg", ".jpg", ".gif", ".svg"]

COMMIT_REGEX = r"([\^a-zA-Z0-9]*)"
DATE_REGEX = r"([0-9]{4})-([0-9]{2})-([0-9]{2})"
TIME_REGEX = r"([0-9]{2}):([0-9]{2}):([0-9]{2})"

REGEX_STRING = COMMIT_REGEX \
    + r"\s*\(([a-zA-Z0-9\s]*)\s*" \
    + DATE_REGEX + r"\s*" \
    + TIME_REGEX + r"\s*" \
    + r"([-+0-9]*)\s*([0-9]*)\)\s*(.*)"


class OutputType:
    def __init__(self, slug, ext):
        self._slug = slug
        self._ext = ext

    def __str__(self):
        return self.slug

    @property
    def slug(self):
        return self._slug

    @property
    def ext(self):
        return self._ext

    @classmethod
    def for_slug(cls, slug):
        for output_type in OutputTypes.__ALL__:
            if output_type.slug == slug:
                return output_type
        raise LookupError(f"There is no output type defined for slug {slug}.")

    @classmethod
    def get_extension(cls, slug):
        return cls.get_for_slug(slug).ext


class OutputTypes(ImmutableSequence):
    CSV = OutputType(slug="csv", ext="csv")
    EXCEL = OutputType(slug="excel", ext="xlsx")
    __ALL__ = [CSV, EXCEL]
    HUMANIZED = humanize_list([ot.slug for ot in __ALL__], conjunction="or")
    VALID_EXTENSIONS = set([ot.ext for ot in __ALL__])

    def __init__(self, *output_types):
        super().__init__([OutputType.for_slug(s) for s in set(output_types)])

    def __str__(self):
        return humanize_list(self.slugs, conjunction="and")

    @property
    def slugs(self):
        return [ot.slug for ot in self]

    def get_extensions(self, include_prefix=True):
        return self.standardize_extensions(
            [ot.ext for ot in self],
            include_prefix=include_prefix
        )

    @classmethod
    def standardize_extension(cls, ext, include_prefix=True):
        ext = ext.lower()
        if not ext.startswith('.') and include_prefix:
            ext = f".{ext}"
        elif ext.startswith('.') and not include_prefix:
            return ext.split('.')[1]
        return ext

    @classmethod
    def standardize_extensions(cls, exts, include_prefix=True):
        return [
            cls.standardize_extension(ext, include_prefix=include_prefix)
            for ext in exts
        ]

    @classmethod
    def validate_general_file_extension(cls, ext, ctx, param):
        if cls.standardize_extension(ext) not in cls.VALID_EXTENSIONS:
            humanized = humanize_list(cls.VALID_EXTENSIONS, conjunction="or")
            raise BadParameter(
                f"The extension {ext.lower()} is not a supported "
                "output file type.  Output files must be of type "
                f"{humanized}.",
                ctx=ctx,
                param=param
            )

    def validate_file_extension(self, ext, ctx, param):
        self.validate_general_file_extension(ext, ctx, param)
        humanized = humanize_list(
            value=[TerminalCodes.bold(s) for s in self.slugs],
            conjunction="and"
        )
        humanized_extensions = humanize_list(
            value=[TerminalCodes.bold(ext) for ext in self.get_extensions()],
            conjunction="and"
        )
        ext = self.standardize_extension(ext)
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


OutputTypes.VALID_EXTENSIONS = OutputTypes.standardize_extensions(
    set([ot.ext for ot in OutputTypes.__ALL__]))


class HelpText:
    FILE_LIMIT = (
        "If this value is set, the blame will only parse files up until this "
        "number has been reached."
    )
    OUTPUT_COLS = "The columns that should be included in any tabular output."
    OUTPUT_FILE = (
        "The name or path of the file that the output will be saved to.  Only "
        "applicable for commands that only generate one output file.\n"
        "- If an extension is not included, the extension will be inferred "
        "from the `outputtype` option."
        "- If omitted, the output file name will be automatically generated "
        "based on the name of the repository and the current branch."
    )
    OUTPUT_DIR = (
        "The directory which output files will be saved to."
        "The name or path of the file that the output will be saved to.  Only "
        "applicable for commands that only generate one output file.\n"
        "- If an extension is not included, the extension will be inferred "
        "from the `outputtype` option."
        "- If omitted, the output file name will be automatically generated "
        "based on the name of the repository and the current branch."
    )
    OUTPUT_TYPE = (
        "The manner in which results should be outputted.  Can be a single "
        f"value or multiple values.  Valid values are {OutputTypes.HUMANIZED}. "
        "If omitted, the output type will be inferred from the provided "
        "output file.  If this cannot be done, the output will only be "
        "displayed via stdout, but will not be saved to a file."
    )

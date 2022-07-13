import pathlib
from click.exceptions import BadParameter

from git_blame_project.utils import iterable_from_args

from .stdout import warning, TerminalCodes
from .utils import humanize_list, ImmutableSequence


def standardize_extension(ext, include_prefix=True):
    ext = ext.lower()
    if not ext.startswith('.') and include_prefix:
        ext = f".{ext}"
    elif ext.startswith('.') and not include_prefix:
        return ext.split('.')[1]
    return ext


def standardize_extensions(exts, include_prefix=True):
    return [
        standardize_extension(ext, include_prefix=include_prefix)
        for ext in exts
    ]


def extensions_equal(ext1, ext2):
    return standardize_extension(ext1) == standardize_extension(ext2)


class OutputFile:
    def __init__(self, path, raw_value):
        self._path = path
        self._raw_value = raw_value

    def __str__(self):
        return str(self.path)

    @property
    def path(self):
        return self._path

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def directory(self):
        return self.path.parent

    @property
    def extension(self):
        return self.path.suffix

    def filepath(self, output_type):
        return self.infer_filename_from_output_type(output_type)

    def infer_filename_from_output_type(self, output_type):
        output_type = OutputType.for_slug(output_type)
        return output_type.format_filename(self.path)


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
        return standardize_extension(self._ext)

    @classmethod
    def for_slug(cls, slug):
        if isinstance(slug, cls):
            return slug
        for output_type in OutputTypes.__ALL__:
            if output_type.slug == slug:
                return output_type
        raise LookupError(f"There is no output type defined for slug {slug}.")

    @classmethod
    def get_extension(cls, slug):
        return cls.get_for_slug(slug).ext

    def format_filename(self, filename):
        if not isinstance(filename, pathlib.Path):
            filename = pathlib.Path(filename)
        return filename.with_suffix(self.ext)


class OutputTypes(ImmutableSequence):
    CSV = OutputType(slug="csv", ext="csv")
    EXCEL = OutputType(slug="excel", ext="xlsx")
    __ALL__ = [CSV, EXCEL]
    HUMANIZED = humanize_list([ot.slug for ot in __ALL__], conjunction="or")
    VALID_EXTENSIONS = set([ot.ext for ot in __ALL__])

    def __init__(self, *output_types):
        output_types = iterable_from_args(*output_types)
        super().__init__([OutputType.for_slug(s) for s in set(output_types)])

    def __str__(self):
        return humanize_list(self.slugs, conjunction="and")

    @classmethod
    def all(cls):
        return cls(cls.__ALL__)

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

    @property
    def slugs(self):
        return [ot.slug for ot in self]

    def get_extensions(self, include_prefix=True):
        return standardize_extensions(
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


OutputTypes.VALID_EXTENSIONS = OutputTypes.standardize_extensions(
    set([ot.ext for ot in OutputTypes.__ALL__]))

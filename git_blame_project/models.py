import pathlib
from click.exceptions import BadParameter

from git_blame_project.utils import (
    iterable_from_args, import_at_module_path, empty)

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
    def __init__(self, path, raw_value, suffix=None):
        self._path = path
        self._raw_value = raw_value
        self._suffix = suffix

    def __str__(self):
        return str(self.path)

    @property
    def path(self):
        if self._suffix is None:
            return self._path
        return self._path.with_stem(self._path.stem + "-" + self._suffix)

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def directory(self):
        return self.path.parent

    @property
    def extension(self):
        return self.path.suffix

    def add_suffix(self, suffix):
        self._suffix = suffix

    def with_suffix(self, suffix):
        return OutputFile(
            path=self._path,
            raw_value=self._raw_value,
            suffix=suffix
        )

    def filepath(self, output_type, suffix=None):
        return self.infer_filename_from_output_type(output_type, suffix=suffix)

    def infer_filename_from_output_type(self, output_type, suffix=None):
        output_type = OutputType.for_slug(output_type)
        if suffix is not None:
            return output_type.format_filename(self.with_suffix(suffix).path)
        return output_type.format_filename(self.path)


class SlugsConfiguration:
    def __init__(self, name, required=False, default=empty):
        self.name = name
        self.required = required
        self.default = default

    def parse(self, model, config_data):
        if config_data is None:
            value = empty
        else:
            value = config_data.get(self.name, empty)
        if value is empty:
            value = self.default
        if value is empty:
            if self.required:
                raise TypeError(
                    f"The configuration {self.name} is required for model "
                    f"{model}."
                )
            return None
        return value


def Slug(plural_model=None, singular_model=None, **options):
    cumulative_options = options.pop('cumulative', None)
    configurations = options.pop('configurations', [])

    if plural_model is None and singular_model is None:
        raise TypeError(
            "A slug model must either define its plural counterpart or its "
            "singular counterpart."
        )
    if singular_model is not None and len(options) == 0:
        raise TypeError(
            "A plural slug model must define `option_attributes`."
        )

    def to_model(value):
        if value is not None and type(value) is str:
            return import_at_module_path(value)
        return value

    def to_model_ref(value):
        if value is not None and type(value) is str:
            return value.split('.')[-1]
        return value

    class MultipleSlugs(ImmutableSequence):
        def __init__(self, *slugs, config=None):
            # The singular model class needs to be dynamically referenced in the
            # case that it requires a dynamic import.
            singular_model_cls = to_model(singular_model)
            # The instances the plural class is initialized with can either be
            # the :obj:`Slug` instances themselves or the string slugs that
            # are associated with specific :obj:`Slug` instances.
            slugs = iterable_from_args(*slugs)
            super().__init__([
                singular_model_cls.for_slug(s) for s in set(slugs)])

            _configurations = getattr(self, 'configurations', configurations)
            for c in _configurations:
                if isinstance(c, dict):
                    c = SlugsConfiguration(**c)
                value = c.parse(self.__class__, config)
                setattr(self, c.name, value)

        def __str__(self):
            return humanize_list(self.slugs, conjunction="and")

        @classmethod
        def all(cls):
            return cls(cls.__ALL__)

        @property
        def slugs(self):
            return [ot.slug for ot in self]

    def pluck_slug(instance_or_cls, *args, **kwargs):
        reference = instance_or_cls
        if not isinstance(instance_or_cls, type):
            reference = instance_or_cls.__class__

        if not hasattr(instance_or_cls, 'slug'):
            if len(args) == 0 and 'slug' not in kwargs:
                raise TypeError(
                    f"The model {reference} does not define the "
                    "slug statically so it must be provided on "
                    "initialization."
                )
            elif len(args) == 1:
                if not isinstance(args[0], str):
                    raise TypeError("The slug must be provided as a string.")
                return args[0]
            elif 'slug' in kwargs:
                if not isinstance(kwargs['slug'], str):
                    raise TypeError("The slug must be provided as a string.")
                return kwargs['slug']
            else:
                raise TypeError(f"Inproper initialization of {reference}.")
        return instance_or_cls.slug

    class SingleSlug:
        def __init__(self, *args, **kwargs):
            self._slug = pluck_slug(self, *args, **kwargs)

        def __new__(cls, *args, **kwargs):
            slug = pluck_slug(cls, *args, **kwargs)

            if not hasattr(cls, 'instances'):
                setattr(cls, 'instances', [])

            if slug not in [i.slug for i in cls.instances]:
                instance = super(SingleSlug, cls).__new__(cls)
                instance.__init__(*args, **kwargs)
                setattr(cls, 'instances', cls.instances + [instance])
            else:
                instance = [i for i in cls.instances if i.slug == slug][0]
            return instance

        def __str__(self):
            return self.slug

        @property
        def slug(self):
            return self._slug

        @classmethod
        def for_slug(cls, slug):
            # The plural model class needs to be dynamically referenced in the
            # case that it requires a dynamic import.
            plural_model_cls = to_model(plural_model)
            if isinstance(slug, cls):
                return slug
            for slug_instance in plural_model_cls.__ALL__:
                if slug_instance.slug == slug:
                    return slug_instance
            raise LookupError(
                f"There is no {cls.__name__} associated with slug {slug}.")

    singular_model_ref = to_model_ref(singular_model)

    def is_singular_model(model):
        # It would be nice to check if the model is an instance of the more
        # specific singular model class in the case that it is specified as
        # an import string, but this would mean actually performing the import
        # which can lead to circular imports.
        if isinstance(singular_model, str):
            return isinstance(model, SingleSlug) \
                and model.__name__ == singular_model.split('.')[-1]
        # We cannot assert that type(model) is singular_model because there
        # are cases where we have a base singular model class and then reference
        # extensions of the base singular model class.
        return isinstance(model, singular_model)

    if singular_model is not None:
        __ALL__ = []
        for k, v in options.items():
            if isinstance(v, dict):
                singular_model_cls = to_model(singular_model)
                v = singular_model_cls(**v)
            elif not is_singular_model(v):
                raise ValueError(
                    f"Encountered type {type(v)} as an option.  Options must "
                    f"be an instance of {singular_model_ref} or a dictionary "
                    "of parameters to initialize an instance of "
                    f"{singular_model_ref}."
                )
            setattr(MultipleSlugs, k.upper(), v)
            __ALL__.append(v)

        setattr(MultipleSlugs, '__ALL__', __ALL__)
        setattr(MultipleSlugs, 'HUMANIZED', humanize_list(
            [m.slug for m in __ALL__], conjunction="or"))

        if cumulative_options is not None:
            cumulative_options = cumulative_options(__ALL__)
            for k, v in cumulative_options.items():
                setattr(MultipleSlugs, k.upper(), v)
        return MultipleSlugs
    return SingleSlug


Slug.Config = SlugsConfiguration


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

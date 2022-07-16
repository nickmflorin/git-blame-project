from git_blame_project.utils import (
    iterable_from_args, import_at_module_path, empty, humanize_list,
    ImmutableSequence)


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

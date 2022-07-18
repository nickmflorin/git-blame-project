import functools

from git_blame_project.utils import (
    iterable_from_args, import_at_module_path, empty, humanize_list)

from .configurable import Configurable, ConfigValue


def to_model(value):
    if value is not None and type(value) is str:
        return import_at_module_path(value)
    return value


def to_model_ref(value):
    if value is not None and type(value) is str:
        return value.split('.')[-1]
    return value


def klass(instance_or_cls):
    if not isinstance(instance_or_cls, type):
        return instance_or_cls.__class__
    return instance_or_cls


def pluck_slug(instance_or_cls, *args, **kwargs):
    reference = klass(instance_or_cls)

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


static_map = {
    (empty, empty): True,
    (True, False): True,
    (False, True): False,
    (True, empty): True,
    (empty, True): False,
    (False, empty): False,
    (empty, False): True
}


def is_static(instance_or_cls, static=empty, dynamic=empty):
    reference = klass(instance_or_cls).__name__
    if (static, dynamic) not in static_map:
        assert (static, dynamic) in [(True, True), (False, False)]
        message = f"{reference} cannot be both static and dynamic."
        if (static, dynamic) == (False, False):
            message = f"{reference} must be static or dynamic."
        raise TypeError(message)
    return static_map[(static, dynamic)]


class SlugBehaviorError(TypeError):
    def __init__(self, instance_or_cls):
        self._cls = klass(instance_or_cls)

    @property
    def message(self):
        raise NotImplementedError()

    def __str__(self):
        return self.message


class StaticSlugError(SlugBehaviorError):
    @property
    def message(self):
        return (
            f"The {self._cls.__name__} model is static and is not "
            "configured."
        )


class DynamicSlugError(SlugBehaviorError):
    @property
    def message(self):
        return (
            f"The {self._cls.__name__} model is dynamic and is already "
            "configured."
        )


def ensure_behavior(behavior, is_property=False):
    assert behavior in ('static', 'dynamic'), \
        "The behavior must either be static or dynamic."

    def decorator(func):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            if behavior == 'static' and not instance.static:
                raise DynamicSlugError(instance)
            elif behavior == 'dynamic' and not instance.dynamic:
                raise StaticSlugError(instance)
            return func(instance, *args, **kwargs)

        if is_property:
            return property(inner)
        return inner
    return decorator


def Slug(**options):
    plural_model = options.pop('plural_model', None)
    singular_model = options.pop('singular_model', None)
    if plural_model is None and singular_model is None:
        raise TypeError(
            "A slug model must either define its plural counterpart or its "
            "singular counterpart."
        )
    if singular_model is not None and len(options) == 0:
        raise TypeError(
            "A plural slug model must define `option_attributes`."
        )

    static_configuration = options.pop('configuration', [])

    class SlugCommon(Configurable):
        def __init__(self, config=None, static=empty, dynamic=empty):
            self._static = is_static(self, static=static, dynamic=dynamic)
            if not self._static:
                self.configure(config=config)

        @property
        def static(self):
            return self._static

        @property
        def dynamic(self):
            return not self._static

        @property
        def static_string(self):
            if self.static is True:
                return "static"
            return "dynamic"

        @ensure_behavior('dynamic', is_property=True)
        def config(self):
            return super().config

        @ensure_behavior('dynamic')
        def configure(self, config=None):
            """
            Configures the instance based on the provided config values and
            attaches the configuration to the instance.

            This method can only be called in the case that the instance is
            dynamic.  This means that if you have a static instance, you cannot
            call this method externally - but rather have to call the
            `to_dynamic` method and provide the configuration values such that
            a new dynamic instance can be created and configured.
            """
            super().configure(config=config)

    # Note: We cannot use the ImmutableSequence class here since that is an
    # ABC Meta class whose metaclass conflicts with the SlugMetaClass.
    class MultipleSlugs(SlugCommon):
        plurality = 'plural'
        configuration = static_configuration

        def __init__(self, *slugs, config=None, static=True):
            # The singular model class needs to be dynamically referenced in the
            # case that it requires a dynamic import.
            singular_model_cls = to_model(singular_model)
            # The instances the plural class is initialized with can either be
            # the :obj:`Slug` instances themselves or the string slugs that
            # are associated with specific :obj:`Slug` instances.
            slugs = iterable_from_args(*slugs)
            self._store = [singular_model_cls.for_slug(s) for s in set(slugs)]
            super().__init__(static=static, config=config)

        @property
        def data(self):
            return self._store

        def __getitem__(self, i):
            return self._store[i]

        def __len__(self):
            return len(self._store)

        def __str__(self):
            humanized = humanize_list(self.slugs, conjunction="and")
            return (
                f"<{self.__class__.__name__} {self.static_string} "
                f"slugs={humanized}>"
            )

        def __repr__(self):
            humanized = humanize_list(self.slugs, conjunction="and")
            return (
                f"<{self.__class__.__name__} {self.static_string} "
                f"slugs={humanized}>"
            )

        @property
        def static(self):
            assert all([s.static == self._static for s in self]), \
                f"The plural slug model {self.__class__} is " \
                f"{self.static_string} but has children that are not " \
                f"{self.static_string}."
            return self._static

        @classmethod
        def all(cls):
            return cls(cls.__ALL__, static=True)

        @ensure_behavior('static')
        def to_dynamic(self, config=None):
            # The individual children slugs should be static because that check
            # is performed in the static @property.
            return self.__class__(
                *[slug.to_dynamic(config=config) for slug in self],
                config=config,
                static=False
            )

        @property
        def slugs(self):
            return [ot.slug for ot in self]

    class SingleSlug(SlugCommon):
        plurality = 'single'
        configuration = static_configuration

        def __init__(self, *args, **kwargs):
            super().__init__(**kwargs)
            self._slug = pluck_slug(self, *args, **kwargs)

        def __new__(cls, *args, **kwargs):
            _static = kwargs.get('static', empty)
            _dynamic = kwargs.get('dynamic', empty)
            static = is_static(cls, static=_static, dynamic=_dynamic)

            slug = pluck_slug(cls, *args, **kwargs)

            if static and not hasattr(cls, 'instances'):
                setattr(cls, 'instances', [])

            if not static or slug not in [i.slug for i in cls.instances]:
                instance = super(SingleSlug, cls).__new__(cls)
                instance.__init__(*args, **kwargs)
                setattr(cls, 'instances', cls.instances + [instance])
            else:
                instance = [i for i in cls.instances if i.slug == slug][0]
            return instance

        def __str__(self):
            return f"<{self.__class__.__name__} {self.slug}>"

        def __repr__(self):
            return f"<{self.__class__.__name__} {self.slug}>"

        def to_dynamic(self, config=None):
            if hasattr(klass(self), 'slug'):
                return self.__class__(config=config, static=False)
            return self.__class__(slug=self._slug, config=config, static=False)

        @property
        def slug(self):
            return self._slug

        @classmethod
        def for_slug(cls, slug, config=None):
            # The plural model class needs to be dynamically referenced in the
            # case that it requires a dynamic import.
            plural_model_cls = to_model(plural_model)
            if isinstance(slug, cls):
                return slug
            for slug_instance in plural_model_cls.__ALL__:
                if slug_instance.slug == slug:
                    if config is not None:
                        return slug_instance.to_dynamic(config=config)
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

    cumulative_options = options.pop('cumulative', None)

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


Slug.Config = ConfigValue

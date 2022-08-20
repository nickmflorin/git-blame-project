from git_blame_project import utils, configurable, exceptions


def to_model(value):
    if value is not None and type(value) is str:
        return utils.import_at_module_path(value)
    return value


def to_model_ref(value):
    if value is not None and type(value) is str:
        return value.split('.')[-1]
    return value


static_map = {
    (utils.empty, utils.empty): True,
    (True, False): True,
    (False, True): False,
    (True, utils.empty): True,
    (utils.empty, True): False,
    (False, utils.empty): False,
    (utils.empty, False): True
}


class SlugNotStaticError(exceptions.GitBlameProjectError):
    required_on_init = ['klass']
    content = [
        "The {klass} is not static."
    ]


ensure_static = exceptions.check_instance(
    exc_cls=SlugNotStaticError,
    exc_kwargs=lambda instance: {"klass": instance},
    criteria=[
        exceptions.Criteria(attr='static')
    ]
)


def is_static(instance_or_cls, static=utils.empty, dynamic=utils.empty):
    reference = utils.klass(instance_or_cls).__name__
    if (static, dynamic) not in static_map:
        assert (static, dynamic) in [(True, True), (False, False)]
        message = f"{reference} cannot be both static and dynamic."
        if (static, dynamic) == (False, False):
            message = f"{reference} must be static or dynamic."
        raise TypeError(message)
    return static_map[(static, dynamic)]


class SingleSlugMetaClass(configurable.ConfigurableMetaClass):
    def __new__(cls, name, bases, dct):
        if len(bases) not in (0, 1):
            raise TypeError("Slugs do not support multiple inheritance.")
        if len(bases) == 1 and bases[0].__name__ != "SlugCommon":
            # We do not allow the `slug` attribute to be defined with an
            # @property for classes that extend the SingleSlug base class.
            if 'slug' in dct and isinstance(dct['slug'], property):
                raise TypeError(
                    "Singular forms of slug models cannot define a `slug` with "
                    "an @property."
                )
        return super().__new__(cls, name, bases, dct)


def Slug(**options):
    """
    A class factory that generates the base class for a slug-based model in
    either its plural form or singular form.  Usage of slug-based models allows
    us to define discrete options for a given entity while allowing those
    options to be easily obtained and associated with each other.

    Terminology:
    -----------
    For the following, we define the following terminology:

    (1) Singular Context
        The class factory is being used to generate the base class of a model
        representing a single slug choice.

    (2) Plural Context
        The class factory is being used to generate the base class of a model
        representing a discrete set of slug choices.

    (3) Singular Form
        A slug model that represents a single slug choice.

        Consider we have a model class, `Fruit` that extends the singular form
        of a slug model.  That is:

        >>> class Fruit(Slug(plural_model=...))
        >>>   ...

        Lets assume that there are only 3 instances of the `Fruit` class that can
        exist:

        >>> Fruit(slug='apple')
        >>> Fruit(slug='banana')
        >>> Fruit(slug='pear')

        As long as the slug instantiation does not include configurations,
        instantiating a singular form of a slug model with a slug that already
        exists will return the same slug instance:

        >>> fruit1 = Fruit(slug='apple', title='Apple')
        >>> fruit2 = Fruit(slug='apple')
        >>> fruit2.title == "Apple"
        >>> fruit1 == fruit2
        >>> True

    (4) Plural Form
        A slug model that represents a discrete set of slug choices (in their
        singular form).  The plural slug model can be instantiated with any
        number of individual slug models, but each model must always correspond
        to a pre-defined discrete instance.

        >>> class Fruits(SlugModel(
        >>>     singular_model=Fruit,
        >>>     choices={
        >>>         'apple': Fruit(slug='apple'),
        >>>         'banana': Fruit(slug='banana'),
        >>>         'pear': Fruit(slug='pear'),
        >>>     }
        >>> ))

        Now, when referring to a single slug choice we can access the model via
        the plural form as follows:

        >>> Fruits.APPLE
        >>> <Fruit apple>

        Any set of `Fruit` models can be in a given `Fruits` set, as long as the
        slugs are discrete choices for the plural model:

        >>> smoothie_fruits = Fruits('apple', 'banana')
        >>> all_fruits = Fruits('apple', 'banana', 'pear')

    (5) Static Form
        If a slug model model cannot be configured, or it has not yet been
        configured, it is considered to be in the "static" form.  All aspects of
        two slug instances will always be the same as long as those slug
        instances are static and have the same "slug":

    (6) Dynamic Form
        Certain slug models (both plural and singular) can be configured with
        certain dynamic attributes.  Unlike other attributes of a slug model,
        configured attributes can differ between two slug instances with the
        same "slug".

        When a static slug model is configured, a new instance of that slug
        model is returned with those configurations applied.  The returned,
        configured instance is now considered "dynamic":

        >>> fruit1 = Fruit(slug='apple', title='Apple')
        >>> fruit2 = Fruit(slug='apple')
        >>> fruit1 == fruit2
        >>> True
        >>> configured = fruit2.configure(config={"count": 5})
        >>> fruit1 == configured
        >>> False
        >>> configured.dynamic
        >>> True

    Parameters:
    ----------
    singular_model: :obj:`type` or :obj:`str` (optional)
        The class that represents the singular form of the slug model.  Can be
        provided as the class itself or the string module path to the class
        (to avoid circular imports).

        Required for the plural context, not applicable for the singular context.
        Default: None

    plural_model: :obj:`type` or :obj:`str` (optional)
        The class that represents the plural form of the slug model.  Can be
        provided as the class itself or the string module path to the class
        (to avoid circular imports).

        Required for the singular context, not applicable for the plural context.
        Default: None

    choices: :obj:`dict` (optional)
        The discrete set of slug models in their singular form that the plural
        form of the slug model can consist of.

        The keys of the provided :obj:`dict` refer to the static attribute name
        of the individual slug instance on the plural slug class and the
        values associated with each key, which represent the singular form of
        the slug model the key is associated with, can be provided as either a
        dictionary mapping of attributes-values that are used to instantiate the
        class defined by the `singular_model` or an instance of the the class
        defined by the `singular_model` itself.

        Example:
        -------
        >>> choices = {"apple": {"slug": "apple", "color": "red"}}
        >>> choices = {"apple": Fruit(slug="apple", color="red")}

        Required for the plural context, not applicable for the singular context.
        Default: None

    configuration: :obj:`Configuration` or :obj:`list` (optional)
        Either a :obj:`Configuration` instance or a :obj:`list` of :obj:`Config`
        instances that define the attributes that the given slug model,
        either in a plural or singular form, can be configured with.

        When the `configuration` is present on a singular or plural form of
        a slug class, that slug class can:

        (1) Be instantiated with a `config` parameter that represents a set
            of configuration values to configure the slug instance with.  In
            this case, the instantiated form of the slug class will be dynamic.

        (2) Be converted to a dynamic form of the slug class with the provided
            set of configuration values applied via the `to_dynamic` method.
            In this case, the method will return a dynamic form of the slug
            instance with the configurations applied.

        Default: None

    cumulative_attributes: :obj:`dict` or :obj:`lambda` (optional)
        Either an :obj:`dict` mapping of static attributes or a callback
        taking the array of discrete slug choices as its argument and returning
        an :obj:`dict` mapping of static attributes.  The static attributes
        will be defined on the plural form of the model class.

        This is used when we need to define attributes on the plural form of
        the slug class that depend on the set of discrete slug choices for
        that class.

        Example:
        -------
        >>> cumulative_attributes = lambda __ALL__: {
        >>>    "valid_slugs": [a.slug for a in __ALL__]
        >>> }

        In this case, the plural form of the slug model will have a `VALID_SLUGS`
        attribute that returns the slugs of all the discrete slug choices for
        that class.

        Only applicable for the plural context.
        Default: None
    """
    # Required if the factory is being used in the singular context.
    plural_model = options.pop('plural_model', None)

    # Required if the factory is being used in the plural context.
    singular_model = options.pop('singular_model', None)

    # Either the plural model or singular model must be defined, otherwise we
    # cannot determine whether or not the base class is being used in the
    # plural or singular context.
    if plural_model is None and singular_model is None:
        raise TypeError(
            "A slug model must either define its plural counterpart or its "
            "singular counterpart."
        )

    # Choices are only applicable in the plural context, and including them
    # for the singular context will raise an error.
    choices = None
    if singular_model is not None:
        choices = options.pop('choices', None)
        if choices is None or len(choices) == 0:
            raise TypeError(
                "The plural form of a slug model must define the individual "
                "discrete slug choices that it can be composed of."
            )
    elif 'choices' in options:
        raise TypeError(
            "The singular form of a slug model cannot define the set of "
            "discrete choices for that slug model."
        )

    configuration = options.pop('configuration', configurable.NotConfigurable)

    class SlugCommon(configurable.Configurable):
        configure_on_init = True

        def __init__(self, config=None, static=utils.empty, dynamic=utils.empty):
            self._static = is_static(self, static=static, dynamic=dynamic)
            # Even though the class extends :obj:`Configurable`, it will not
            # have the behaviors and properties of a configurable class if the
            # `configuration` attribute is not defined or inherited.  In this
            # case, the class will define `is_configurable`
            # If the slug is not configurable,
            super(SlugCommon, self).__init__(config=config)

        @property
        def static(self):
            return self._static

        @property
        def dynamic(self):
            return not self._static

        @property
        def state_string(self):
            if self.static is True:
                return "static"
            return "dynamic"

        @property
        def can_configure(self):
            # Configuration can only be performed if the instance is dynamic.
            # This means that if you have a static instance, you cannot
            # configure it externally - but must use the `to_dynamic` method
            # to instantiate a new dynamic instance which is then configured.
            if self.static:
                return f"The {self.__class__.__name__} instance is static."
            return True

    # Note: We cannot use the ImmutableSequence class here since that is an
    # ABC Meta class whose metaclass conflicts with the SlugMetaClass.
    class MultipleSlugs(SlugCommon):
        plurality = 'plural'

        def __init__(self, *slugs, config=None, static=True):
            # The singular model class needs to be dynamically referenced in the
            # case that it requires a dynamic import.
            singular_model_cls = to_model(singular_model)
            # The instances the plural class is initialized with can either be
            # the :obj:`Slug` instances themselves or the string slugs that
            # are associated with specific :obj:`Slug` instances.
            slugs = utils.iterable_from_args(*slugs)
            self._store = [singular_model_cls.for_slug(s) for s in set(slugs)]
            super().__init__(static=static, config=config)

        @property
        def data(self):
            return self._store

        def __getitem__(self, i):
            return self._store[i]

        def __len__(self):
            return len(self._store)

        @property
        def slugs(self):
            return [ot.slug for ot in self]

        def __str__(self):
            humanized = utils.humanize_list(self.slugs, conjunction="and")
            return (
                f"<{self.__class__.__name__} {self.state_string} "
                f"slugs={humanized}>"
            )

        def __repr__(self):
            humanized = utils.humanize_list(self.slugs, conjunction="and")
            return (
                f"<{self.__class__.__name__} {self.state_string} "
                f"slugs={humanized}>"
            )

        @property
        def static(self):
            # If the plural form of the slug model is static, all of its
            # children must
            assert all([s.static == self._static for s in self]), \
                f"The plural slug model {self.__class__} is " \
                f"{self.state_string} but has children that are not " \
                f"{self.state_string}."
            return self._static

        @classmethod
        def all(cls):
            return cls(cls.__ALL__, static=True)

        @ensure_static
        def to_dynamic(self, config=None):
            """
            Returns a new dynamic instance of the :obj:`MultipleSlugs` with the
            provided configurations applied.  All individual instances of
            :obj:`SingleSlug` that the instance contains are also converted
            to dynamic instances with the configurations applied.
            """
            # The individual children slugs should be static because that check
            # is performed in the static @property.
            return self.__class__(
                *[slug.to_dynamic(config=config) for slug in self],
                config=config,
                static=False
            )

    class SingleSlug(SlugCommon, metaclass=SingleSlugMetaClass):
        plurality = 'single'

        def __init__(self, *args, **kwargs):
            super().__init__(**kwargs)
            self._slug = self.pluck_slug(*args, **kwargs)

        def __new__(cls, *args, **kwargs):
            _static = kwargs.get('static', utils.empty)
            _dynamic = kwargs.get('dynamic', utils.empty)
            static = is_static(cls, static=_static, dynamic=_dynamic)

            slug = cls.pluck_slug(*args, **kwargs)

            if static and not hasattr(cls, 'instances'):
                setattr(cls, 'instances', [])

            if not static or slug not in [i.slug for i in cls.instances]:
                instance = super(SingleSlug, cls).__new__(cls)
                setattr(cls, 'instances', cls.instances + [instance])
            else:
                instance = [i for i in cls.instances if i.slug == slug][0]
            return instance

        def __str__(self):
            # The slug may not be defined if the instance has not been fully
            # initialized yet.
            if hasattr(self, '_slug'):
                return f"<{self.__class__.__name__} {self.slug}>"
            return f"<{self.__class__.__name__} ...>"

        def __repr__(self):
            # The slug may not be defined if the instance has not been fully
            # initialized yet.
            if hasattr(self, '_slug'):
                return f"<{self.__class__.__name__} {self.slug}>"
            return f"<{self.__class__.__name__} ...>"

        @classmethod
        def pluck_slug(cls, *args, **kwargs):
            static_slug = getattr(cls, 'slug', None)
            # The `slug` is not allowed to be defined as an @property because
            # it must be accessible from the class itself.  The metaclass
            # should prevent this, but we check just to be sure.
            if static_slug is None or isinstance(static_slug, property):
                # If the model does not define the slug statically, it must be
                # provided as an argument or keyword argument.
                if len(args) != 0:
                    if not isinstance(args[0], str):
                        raise exceptions.InvalidParamError(
                            param='slug',
                            valid_types=(str, ),
                            value=args[0]
                        )
                    elif len(args) != 1:
                        raise exceptions.ImproperUsageError(
                            message=f"Expected a single argument, the `slug`, "
                            f"but received {len(args)} arguments."
                        )
                    return args[0]
                elif 'slug' in kwargs:
                    if not isinstance(kwargs['slug'], str):
                        raise exceptions.InvalidParamError(
                            param='slug',
                            valid_types=(str, ),
                            value=kwargs['slug']
                        )
                    return kwargs["slug"]
                raise exceptions.RequiredParamError(param='slug')
            return cls.slug

        @ensure_static
        def to_dynamic(self, config=None):
            """
            Returns a new dynamic instance of the :obj:`SingleSlug` with the
            provided configurations applied.
            """
            if hasattr(utils.klass(self), 'slug'):
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

    if singular_model is not None:
        singular_model_cls = to_model(singular_model)

        # For each choice, set the choice on the plural form of the class with
        # the upper case choice name.  Additionally, keep track of all the
        # choices for the plural form of the class such that the plural form
        # of the class can be attributed with an __ALL__ property.
        __ALL__ = []
        for k, v in choices.items():
            if isinstance(v, dict):
                v = singular_model_cls(**v)
            elif not is_singular_model(v):
                raise ValueError(
                    f"Encountered type {type(v)} as an option.  Options must "
                    f"be an instance of {singular_model_ref} or a dictionary "
                    "of parameters to initialize an instance of "
                    f"{singular_model_ref}."
                )
            if not v.static:
                raise ValueError(
                    "The provided slug choices for the plural form of the slug "
                    "class must always be static."
                )
            setattr(MultipleSlugs, k.upper(), v)
            __ALL__.append(v)

        setattr(MultipleSlugs, '__ALL__', __ALL__)

        # For each cumulative attribute, set the attribute on the class based
        # on the upper case attribute name.
        cumulative_attributes = options.pop('cumulative_attributes', {})
        if not isinstance(cumulative_attributes, dict):
            cumulative_attributes = cumulative_attributes(__ALL__)
        # Each plural slug class should have a `HUMANIZED` attribute which
        # returns a humanized string of all of the available slug choices.
        cumulative_attributes.update(humanized=utils.humanize_list(
            [m.slug for m in __ALL__],
            conjunction="or"
        ))
        for k, v in cumulative_attributes.items():
            setattr(MultipleSlugs, k.upper(), v)

        # Do not set the configuration on both the plural form and singular form
        # of the slug classes statically - only one form is returned and one
        # form is needed, and setting the configuration on both instances will
        # cause collisions between the :obj:`Config` instances and the class
        # they are bound to.
        setattr(MultipleSlugs, 'configuration', configuration)
        return MultipleSlugs

    if 'cumulative_attributes' in options:
        raise TypeError(
            "The cumulative attributes are only applicable for the plural form "
            "of the slug model."
        )
    # Do not set the configuration on both the plural form and singular form
    # of the slug classes statically - only one form is returned and one
    # form is needed, and setting the configuration on both instances will
    # cause collisions between the :obj:`Config` instances and the class
    # they are bound to.
    setattr(SingleSlug, 'configuration', configuration)
    return SingleSlug

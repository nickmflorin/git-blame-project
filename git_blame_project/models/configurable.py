import functools
import inspect

from git_blame_project import stdout
from git_blame_project.exceptions import GitBlameProjectError
from git_blame_project.utils import (
    iterable_from_args, empty, humanize_list, ImmutableSequence, humanize_dict,
    LazyFn, is_function)


class ConfigError(GitBlameProjectError):
    """
    Raised when there is an error related to a specific configuration value.
    The default behavior is to indicate that the configuration is simply
    invalid - other error should be associated with extended classes.
    """
    object_required = True

    def __init__(self, name, *args, **kwargs):
        self._name = name
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self._name

    @property
    def message_prefix(self):
        return f"There was an error configuring {self.cls.__name__}"

    @property
    def content(self):
        return f"The configuration `{self.name}` is invalid."


class ConfigRequiredError(ConfigError):
    @property
    def content(self):
        return (
            f"The configuration `{self.name}` is required but was not "
            "provided."
        )


class ConfigurationError(GitBlameProjectError):
    """
    Raised when an instance cannot be configured.
    """
    object_required = True

    @property
    def message_prefix(self):
        return f"The class {self.cls.__name__} cannot be configured"


class Config:
    """
    Represents a single configuration value for a configurable class.

    Terminology:
    -----------
    We refer to the following terms:

    (1) Value Set:
        Refers to the set of configuration values that are provided to the
        instance when being configured.  The values can either be provided
        as a :obj:`dict` or a :obj:`Configuration` instance.  When being
        configured, the value of :obj:`Config` instance in the set of overall
        configurations on the class are located in the Configuration Set.

    (2) Missing
        Refers to whether or not the value associated with the :obj:`Config`
        is missing from the provided value set or has a null value when the
        parameter `allow_null` is False.

        Parameter = "fooey"
        Value Set = {"foo": 5, "bar": 10}
        --> Value is Missing

        Parameter = "fooey"
        Value Set = {"foo": 5, "bar": 10, "fooey": None}
        Allow Null = False
        --> Value is Missing

        Parameter = "fooey"
        Value Set = {"foo": 5, "bar": 10, "fooey": None}
        Allow Null = True
        --> Value is Not Missing

    Parameters:
    ----------
    name: :obj:`str`
        The name of the configuration.  This parameter dictates what attribute
        the parsed value of the :obj:`Config` instance will be stored as on the
        :obj:`Configuration` instance.

    accessor: :obj:`str` (optional)
        The attribute of the :obj:`Configuration` or the key of the :obj:`dict`
        that is associated with the value of the :obj:`Config`.  However, the
        `name` parameter also dictates the attribute of the overall
        :obj:`Configuration` that the value associated with the :obj:`Config`
        instance should be stored under.

        There are cases where we may want to save the value associated with the
        :obj:`ConfigValue` under a different attribute name than the one that
        needs to be used to read the value from the value set.

        In this case, the `accessor` can be explicitly provided, and the
        value will be read using the `accessor` parameter but still saved using
        the `name` parameter.

        Default: Value of the `name` parameter.

    required: :obj:`bool` (optional)
        Whether or not the :obj:`Config` is required.

        In the case that the :obj:`Config` is required, the following hold:

        (1) If the accessor associated with the :obj:`Config` does not exist
            in the value set provided to the :obj:`Config` instance, an error
            will be raised.

        (2) If the accessor associated with the :obj:`Config` exists in the
            value set provided to the :obj:`Config` instance, but has a value
            of `None` - an error will be raised if `allow_null` is False.
            Otherwise, the `None` value will simply be used as the resulting
            value associated with the :obj:`Config`.

        Note that if the `default` parameter is provided, a missing value
        will not raise an error in the case that the :obj:`Config` is required
        because the default is applied before it is determined whether or not
        the value is missing from the provided value set.

        Default: False

    allow_null: :obj:`bool` (optional)
        Whether or not null values are allowed for the :obj:`Config` instance.
        If null values are not allowed, a value of `None` that exists for a
        given accessor in the value set will be treated as a missing value, and
        an error will be raised in the case that the :obj:`Config` is required.

        Default: False

    default: (optional)
        If the `default` is provided and the value is considered missing
        from the provided value set, the value defined by this `default`
        parameter will be used.

        The `default` parameter can be specified as an intrinsic type (string,
        int, etc), a function that takes 0 arguments, a function that takes the
        instance as it's first and only argument, or an instance of
        :obj:`LazyFn`.

        Default: empty (i.e. Not Provided)

    formatter: :obj:`lambda` (optional)
        A callback that is used to format the value after it is read from the
        provided value set but before it is stored on the overall
        :obj:`Configuration` instance.

        Default: None
    """
    def __init__(self, name, **kwargs):
        self._name = name
        self._required = kwargs.pop('required', False)
        self._default = kwargs.pop('default', empty)
        self._formatter = kwargs.pop('formatter', None)
        self._allow_null = kwargs.pop('allow_null', False)

        # The name of the attribute that is used to read the associated
        # configuration value.  If not provided, the name of the attribute
        # defined by the `name` parameter is used.
        self._accessor = kwargs.pop('accessor', None)

    def __str__(self):
        return f"<Config name={self.name}>"

    def __repr__(self):
        return f"<Config name={self.name}>"

    @property
    def name(self):
        return self._name

    @property
    def required(self):
        return self._required

    @property
    def formatter(self):
        return self._formatter

    @property
    def allow_null(self):
        return self._allow_null

    @property
    def accessor(self):
        return self._accessor or self.name

    @property
    def default(self):
        return self._default

    def read(self, instance, config_obj):
        """
        Reads the value associated with the `name` of the :obj:`Config`
        instance from provided configuration set, provided either as a
        :obj:`dict` mapping of values or
        """
        if config_obj is None:
            raise ConfigRequiredError(self.accessor, cls=instance)
        if isinstance(config_obj, Configuration):
            return getattr(config_obj, self.accessor)
        return config_obj.get(self.accessor, empty)

    def default_value(self, instance):
        """
        Returns the default value for the provided instance based on the
        `default` parameter that was defined on initialization.

        The `default` parameter can be defined as one of the following:

        (1) An intrinsic, non-callable attribute (like a str or int).
        (2) An instance of :obj:`LazyFn` - which will call the original function
            with the arguments and keyword arguments that the :obj:`LazyFn` was
            initialized with.
        (3) A callback function:
            (a) A callback function that takes 0 arguments.
            (b) A callback function that takes a single argument; the instance
                being configured.
        """
        if isinstance(self.default, LazyFn):
            return self.default()
        elif is_function(self.default):
            argspec = inspect.getfullargspec(self.default)
            if len(argspec.args) == 0:
                return self.default()
            elif len(argspec.args) == 1:
                return self.default(instance)
            raise TypeError(
                "If the default value is a callable, it must either take 0 "
                "arguments or 1 argument - the instance associated with the "
                "configuration."
            )
        return self.default

    def is_missing(self, value):
        return value is empty or (not self.allow_null and value is None)

    def parse(self, instance, config_obj):
        # Keep track of whether or not the value was defaulted such that the
        # formatter is only applied to values that were not defaulted.
        default_used = False

        value = empty
        if config_obj is not None:
            value = self.read(instance, config_obj)

        # If the value is missing, use the default value (which can still be
        # empty if the default is not defined).
        if self.is_missing(value):
            if self.default is not empty:
                value = self.default_value(instance)
                default_used = True

        # If the value is still missing after the default was applied, we need
        # to either raise an error or return a None value.
        if self.is_missing(value):
            if self.required:
                raise ConfigRequiredError(self.accessor, cls=instance)
            return None
        # If a default value is provided, it should be provided in its
        # formatted form.
        if not default_used and self.formatter is not None:
            return self.formatter(value)
        return value


def merge_configurations(*args, existing=None):
    """
    Standardizes the provided configuration instances and merges them with
    the existing configuration instances if provided.

    If duplicates are encountered, either in a specific existing or new
    set of configurations or between the existing set and new set of
    configurations, warnings will be logged.
    """
    def standardize(*a):
        flattened = []
        for c in iterable_from_args(*a):
            config_value = c
            if not isinstance(config_value, Config):
                config_value = Config(**c)
            flattened.append(config_value)
        return flattened

    def add_and_track_duplicates(*configurations, existing=None):
        configurations = standardize(*configurations)
        filtered = []
        duplicated = set([])
        if existing:
            # The existing configurations should always be instances of
            # Config but just in case we will standardize them.
            filtered = standardize(existing)
        for c in configurations:
            if c.name in [o.name for o in filtered]:
                # Store the duplicated configuration values such that we can
                # issue a log afterwards.
                duplicated.add(c.name)
                # Remove the duplicated configuration so the configuration
                # defined afterwards is used.
                filtered = [o for o in filtered if o.name != c.name]
            filtered += [c]
        return filtered, duplicated

    # First, determine the set of unique configurations being added and issue
    # a warning about duplicated configurations in the set being added.
    configurations, duplicated = add_and_track_duplicates(*args)
    if duplicated:
        humanized = humanize_list(duplicated, conjunction="and")
        stdout.log(
            f"Encountered duplicate configurations for {humanized}. "
            "For each duplicated configuration, the configuration defined "
            "last will be used."
        )
    # Then, merge the unique set of configurations with the existing set,
    # keeping track of configurations that are already present in the existing
    # set.
    if existing:
        configurations, duplicated = add_and_track_duplicates(
            *configurations,
            existing=existing
        )
        if duplicated:
            humanized = humanize_list(duplicated, conjunction="and")
            stdout.log(
                f"The configurations {humanized} already exist as "
                "configuration values and will be overwritten."
            )
    return configurations


class Configuration(ImmutableSequence):
    """
    A class that has the behaviors of an iterable type that represents a set of
    :obj:`Config` instances that are attached to a configurable instance.
    """
    def __init__(self, *args):
        self._configuration = {}
        standardized = merge_configurations(*args)
        self._was_configured = False
        super().__init__(*standardized)

    def __str__(self):
        humanized = humanize_dict(self._configuration)
        return f"<{self.__class__.__name__} {humanized}>"

    def __repr__(self):
        humanized = humanize_dict(self._configuration)
        return f"<{self.__class__.__name__} {humanized}>"

    def __getattr__(self, k):
        if k in self._configuration:
            return self._configuration[k]
        elif not self._was_configured:
            raise AttributeError("The configuration was not yet parsed.")
        raise AttributeError(f"No configuration is defined for `{k}`.")

    def add_configurations(self, *configuration):
        self._store = merge_configurations(*configuration, self._store[:])

    def parse(self, instance, config_obj):
        for c in self:
            self._configuration[c.name] = c.parse(instance, config_obj)
        self._was_configured = True


class ConfigurableMetaClass(type):
    """
    A meta class for classes that extend :obj:`Configurable`.  This meta class
    is responsible for merging configurations defined statically on a child
    class with configurations defined statically on the parent class it
    extends.

    Example
    -------
    The base class, :obj:`BaseClass`, defines configurations statically such that
    instances of :obj:`BaseClass` can be configured with attributes defined by
    the :obj:`Config` instances in the configuration.

    >>> class BaseClass(Configurable):
    >>>     configurations = [
    >>>         Config(name='foo', required=False, default=5),
    >>>         Config(name='bar', required=False, default='foo')
    >>>     ]

    The class :obj:`ChildClass` also defines configurations statically on the
    class, but since :obj:`ChildClass` extends :obj:`BaseClass` the overall
    configurations defined on :obj:`ChildClass` will be both those defined on
    :obj:`BaseClass` and those defined on :obj:`ChildClass`.

    >>> class ChildClass(BaseClass):
    >>>     configurations = [
    >>>         Config(name='foo', required=True),
    >>>         Config(name='status', default='ACTIVE')
    >>>     ]

    If there are configurations for the same name on both classes, the
    :obj:`Config` defined on the extended class, :obj:`ChildClass` takes
    priority over the :obj:`Config` that are defined on the base class,
    :obj:`BaseClass`.

    >>> c = ChildClass()

    The configuration `bar` is still configurable on :obj:`ChildClass` since it
    is defined on :obj:`BaseClass`, but it is not required.

    >>> c.configure(foo=10, status='INACTIVE')
    >>> c.config.bar
    >>> "foo"

    The configuration `foo` is defined on both :obj:`ChildClass` and
    :obj:`BaseClass` - but it is required on :obj:`ChildClass` so not including
    it in the provided configurations will result in an error:

    >>> c.configure(status='INACTIVE')
    >>>

    >>> c.config.foo
    >>> 10
    >>> c.config.status
    >>> "INACTIVE"
    >>> c.config.bar
    >>> "foo"
    """
    def __new__(cls, name, bases, dct):
        if len(bases) not in (0, 1):
            raise TypeError(
                f"Classes that extend {Configurable} cannot use mulitple "
                "inheritance."
            )
        if len(bases) == 1:
            # We do not allow the `configuration_allowed` method to be
            # overridden.  Instead the `can_configure` method should be defined.
            if 'configuration_allowed' in dct:
                raise TypeError(
                    f"The class {name} overrides the method "
                    "`configuration_allowed` which is not allowed.  Instead, "
                    "override the `can_configure` method."
                )
            if hasattr(bases[0], 'configuration') and 'configuration' in dct:
                dct['configuration'] = merge_configurations(
                    dct['configuration'],
                    existing=getattr(bases[0], 'configuration')
                )
        return super().__new__(cls, name, bases, dct)


def ensure_configurability(is_property=False):
    """
    A decorator for a instance method or property that ensures that the instance
    is in a state that can be configured before it allows for configuration to
    occur.

    If there are certain states of an instance that should prevent configuration,
    the instance should implement a `can_configure` property.  If the instance
    does not implement the `can_configure` property, it will be treated as if
    it can be configured.

    If implemented, the `can_configure` property should evaluate whether or not
    the instance is in a state that disallows configuration.  IF it is in a
    state that disallows configuration, it should return False or a string error
    message.  If the property returns anything else - it will be treated as
    being in a state that allows configuration.
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            # When the decorator is being applied to a method, the strict
            # parameter dictates whether or not an exception should be raised or
            # the method should simply not be evaluated.
            strict = True
            if not is_property:
                strict = kwargs.pop('strict', True)

            if len(instance.configuration) == 0:
                if not strict:
                    return None
                instance.raise_cannot_configure(
                    reason=f"The {instance.__class__} does not define any "
                    "configurations."
                )
            can_configure = getattr(instance, 'can_configure', True)
            if can_configure is False or isinstance(can_configure, str):
                if not strict:
                    return None
                instance.raise_cannot_configure(
                    instance=instance,
                    reason=can_configure if isinstance(can_configure, str)
                        else None
                )
            return func(instance, *args, **kwargs)
        if is_property:
            return property(inner)
        return inner
    return decorator


class Configurable(metaclass=ConfigurableMetaClass):
    """
    An abstract class that represents an object that can be configured.  When
    the instance is configured, the configuration values are stored on a
    :obj:`Configuration` instance that is attached to the instance this
    class represents.
    """
    def __init__(self, config=None):
        self._was_configured = False
        # pylint: disable=unexpected-keyword-arg
        # Only configure the instance on initialization if it is capable of
        # being configured.
        self.configure(config, strict=False)

    def raise_cannot_configure(self, reason=None):
        """
        Raises an exception that indicates that the configurable instance
        cannot be configured given its current state.

        If a custom exception class is desired, it can be defined statically
        on the class as `cannot_configure_exc`.
        """
        exc_class = getattr(
            self, 'cannot_configure_exc', ConfigurationError) \
            or ConfigurationError
        raise exc_class(self, message_content=reason)

    @property
    def configuration_allowed(self):
        """
        Returns whether or not the configurable instance is allowed to be
        configured given its current state.

        This method should not be overridden.  If there are certain states of
        an instance that should disallow configuration, the instance should
        implement a `can_configure` property.
        """
        if len(self.configuration) == 0:
            return False
        can_configure = getattr(self, 'can_configure', True)
        if can_configure is False or isinstance(can_configure, str):
            return False
        return True

    @property
    def conguration(self):
        """
        Either an instance of :obj:`Configuration` or an iterable of
        :obj:`Config` instances that define the configuration attributes that
        should be associated with an instance of the class.

        This property must be defined statically on the class.  Additionally,
        if a class defines a configuration and that class extends another
        class that defines a configuration, the configurations will be
        merged together in the child class.
        """
        raise NotImplementedError()

    @ensure_configurability(is_property=True)
    def config(self):
        if not hasattr(self, '_config'):
            raise TypeError(
                f"The instance {self.__class__} was not configured.")
        return self._config

    @ensure_configurability()
    def configure(self, config=None):
        """
        Configures the instance based on the provided config values and attaches
        the configuration to the instance.
        """
        self._config = self.configuration
        if not isinstance(self._config, Configuration):
            self._config = Configuration(*self._config)
        self._config.parse(self, config)
        self._was_configured = True

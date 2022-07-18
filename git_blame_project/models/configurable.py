import inspect

from git_blame_project.stdout import log
from git_blame_project.utils import (
    iterable_from_args, empty, humanize_list, ImmutableSequence, humanize_dict,
    Callback, is_function)


class ConfigValue:
    def __init__(self, name, **kwargs):
        self._name = name
        self._required = kwargs.pop('required', False)
        self._default = kwargs.pop('default', empty)
        self._formatter = kwargs.pop('formatter', None)
        self._allow_null = kwargs.pop('allow_null', False)

        # The `accessor_name` is used to read the configuration value from the
        # provided dictionary or Configuration object.  It is only provided in
        # the case that the attribute that we read the configuration value from
        # differs from the attribute that we store the configuration value as
        # (i.e. the `name` property.)
        self._accessor_name = kwargs.pop('accessor_name', None)

    def __str__(self):
        return f"<ConfigValue {self.name}>"

    def __repr__(self):
        return f"<ConfigValue {self.name}>"

    @property
    def name(self):
        return self._name

    @property
    def lookup(self):
        return self._accessor_name or self._name

    def read(self, config_obj):
        assert config_obj is not None, \
            "Can only read from non-null config dictionary objects or " \
            "Configuration instances."
        if isinstance(config_obj, Configuration):
            return getattr(config_obj, self.lookup)
        return config_obj.get(self.lookup, empty)

    def default_value(self, instance):
        if isinstance(self._default, Callback):
            return self._default()
        elif is_function(self._default):
            argspec = inspect.getfullargspec(self._default)
            if len(argspec.args) == 0:
                return self._default()
            elif len(argspec.args) == 1:
                return self._default(instance)
            raise TypeError(
                "If the default value is a callable, it must either take 0 "
                "arguments or 1 argument - the instance associated with the "
                "configuration."
            )
        return self._default

    def parse(self, instance, config_obj):
        value = empty
        default_used = False
        if config_obj is not None:
            value = self.read(config_obj)
        if value is empty or (not self._allow_null and value is None):
            value = self.default_value(instance)
            default_used = True
        if value is empty or (not self._allow_null and value is None):
            if self._required:
                raise TypeError(
                    f"The configuration {self.name} is required for model "
                    f"{instance.__class__}."
                )
            return None
        if not default_used and self._formatter is not None:
            return self._formatter(value)
        return value


def merge_configurations(*args, existing=None):
    def standardize(*a):
        flattened = []
        for c in iterable_from_args(*a):
            config_value = c
            if not isinstance(config_value, ConfigValue):
                config_value = ConfigValue(**c)
            flattened.append(config_value)
        return flattened

    def add_and_track_duplicates(*configurations, existing=None):
        configurations = standardize(*configurations)
        filtered = []
        duplicated = set([])
        if existing:
            # The existing configurations should always be instances of
            # ConfigValue but just in case we will standardize them.
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
        log(
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
            log(
                f"The configurations {humanized} already exist as "
                "configuration values and will be overwritten."
            )
    return configurations


class Configuration(ImmutableSequence):
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
    def __new__(cls, name, bases, dct):
        if len(bases) not in (0, 1):
            raise TypeError(
                f"The class {name} only supports single inheritance.")

        if len(bases) == 1:
            if hasattr(bases[0], 'configuration') and 'configuration' in dct:
                dct['configuration'] = merge_configurations(
                    dct['configuration'],
                    existing=getattr(bases[0], 'configuration')
                )
        return super().__new__(cls, name, bases, dct)


class Configurable(metaclass=ConfigurableMetaClass):
    @property
    def config(self):
        if not hasattr(self, '_config'):
            raise TypeError(
                f"The instance {self.__class__} was not configured.")
        return self._config

    def configure(self, config=None):
        """
        Configures the instance based on the provided config values and attaches
        the configuration to the instance.
        """
        self._config = self.configuration
        if not isinstance(self._config, Configuration):
            self._config = Configuration(*self._config)
        self._config.parse(self, config)

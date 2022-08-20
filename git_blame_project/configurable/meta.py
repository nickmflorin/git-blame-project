from git_blame_project import utils, exceptions

from .config import Config
from .decorators import ensure_configurability, ensure_configured
from .exceptions import ConfigLookupError
from .utils import (
    standardize_configurations, ConfigurationNotSpecified, NotConfigurable)


class ConfigurableMetaClass(type):
    """
    A meta class for classes that extend :obj:`Configurable`.  This meta class
    is responsible for managing attributes associated with :obj:`Config`
    instances defined on the class via the `configuration` static attribute
    while implementing configuration related behavior and properties on the
    class.

    When an attribute is defined via a :obj:`Config` instance, this meta
    class will set those attributes on the configurable class as descriptors -
    which are capable of managing the mannner in which these attributes are
    accessed and set on the configurable class instance.

    If the attribute associated with a :obj:`Config` instance is also set on
    the class explicitly as a static attribute or an @property, those
    attributes and @property(s) are replaced with the descriptor associated
    with the relevant attribute such that the original values represented
    by those set attributes and @property(s) are still captured in the
    descriptors, but the added benefits of the :obj:`Config` desciptor related
    to the accessing and setting of those attributes are still present on the
    class.

    Furthermore, this metaclass will merge configurations specified via
    :obj:`Config` descriptor instances between parent and children classes.

    Example
    -------
    The base class, :obj:`BaseClass`, defines configurations statically such that
    instances of :obj:`BaseClass` can be configured with attributes defined by
    the :obj:`Config` instances in the configuration.

    >>> class BaseClass(Configurable):
    >>>     configurations = [
    >>>         Config(param='foo', required=False, default=5),
    >>>         Config(param='bar', required=False, default='foo')
    >>>     ]

    The class :obj:`ChildClass` also defines configurations statically on the
    class, but since :obj:`ChildClass` extends :obj:`BaseClass` the overall
    configurations defined on :obj:`ChildClass` will be both those defined on
    :obj:`BaseClass` and those defined on :obj:`ChildClass`.

    >>> class ChildClass(BaseClass):
    >>>     configurations = [
    >>>         Config(param='foo', required=True),
    >>>         Config(param='status', default='ACTIVE')
    >>>     ]

    If there are configurations for the same name on both classes, the
    :obj:`Config` defined on the extended class, :obj:`ChildClass` takes
    priority over the :obj:`Config` that are defined on the base class,
    :obj:`BaseClass`.

    >>> c = ChildClass()

    The configuration `bar` is still configurable on :obj:`ChildClass` since it
    is defined on :obj:`BaseClass`, but it is not required.

    >>> c.configure(foo=10, status='INACTIVE')
    >>> c.bar
    >>> "foo"
    """
    def __new__(cls, n, bs, dct):
        def mutated_class(d=None, can_configure=utils.empty):
            d = d or dct
            klass = super(ConfigurableMetaClass, cls).__new__(cls, n, bs, d)
            # TODO: Do we need to remove the methods from the klass in the case
            # that it is not configurable but has inherited configurable
            # methods from the parent?
            if can_configure is not utils.empty:
                setattr(klass, 'is_configurable', can_configure)
            return klass

        # Do not mutate the base :obj:`Configurable` class itself.
        if len(bs) == 0:
            return mutated_class()

        klass_configuration = cls.get_current_configurations(dct)
        # If the current class explicitly defines itself as not being
        # configurable, do not allow it to be configurable - regardless of
        # base class configurations.
        if klass_configuration is NotConfigurable:
            return mutated_class(can_configure=False)

        base_configurations = cls.get_base_configurations(bs)

        # If the current class does not specify a configuration and there are
        # no configurations from any base class, do not allow the class to be
        # configurable.
        if klass_configuration is ConfigurationNotSpecified \
                and len(base_configurations) == 0:
            return mutated_class(can_configure=False)

        # At this point, the class is being treated as configurable.
        if klass_configuration is not ConfigurationNotSpecified:
            base_configurations += [klass_configuration]
        klass_configuration = utils.merge_without_duplicates(
            *base_configurations,
            attr='param',
            # If duplicate values are detected, always choose the unconfigured
            # instance.
            prioritized=lambda c: not c.was_configured
        )

        @ensure_configurability(is_property=True)
        @ensure_configured
        def defaulted_configurations(instance):
            return [c for c in instance.configuration if c.was_defaulted]

        @ensure_configurability
        @ensure_configured
        def configuration_was_defaulted(instance, param):
            if param not in [c.param for c in instance.configuration]:
                raise ConfigLookupError(param=param)
            return param in [c.param for c in instance.defaulted_configurations]

        @ensure_configurability(is_property=True)
        def was_configured(instance):
            return instance._was_configured

        @ensure_configurability
        def configure(instance, config=None):
            """
            Configures the instance based on the provided config values and
            attaches the configuration to the instance.
            """
            for cfg in instance.configuration:
                cfg.configure(instance, config=config)
            instance._was_configured = True

        dct['configuration'] = klass_configuration
        klass = mutated_class(dct, can_configure=True)

        setattr(klass, 'configure', configure)
        setattr(klass, 'was_configured', was_configured)
        setattr(klass, 'defaulted_configurations', defaulted_configurations)
        setattr(
            klass, 'configuration_was_defaulted', configuration_was_defaulted)

        for config in klass_configuration:
            # Note: For :obj:`Config` instances defined on a parent class,
            # they will be rebound to the child class.
            config.bind(klass)
            setattr(klass, config.param, config)
        return klass

    @classmethod
    def get_base_configurations(cls, bases):
        """
        Accumulates the individual :obj:`Config` instances defined on each
        base class.

        When inspecting the `configuration` attribute of a base class, it is
        important to note that if that base class extends :obj:`Configurable`
        or leverages this :obj:`ConfigurableMetaClass` meta class, an invalid
        value for the `configuration` attribute would have already raised an
        exception when the class is created.

        However, if that base class is a mixin, or does not extend
        :obj:`Configurable` or leverage the :obj:`ConfigurableMetaClass` meta
        class, it is not guaranteed that the `configuration` attribute is valid.

        In cases where a base class defines an invalid `configuration` attribute,
        and does not extend :obj:`Configurable` or leverage the
        :obj:`ConfigurableMetaClass` meta class, we do not want to raise an
        exception - we simply just ignore it.  In this way, the `configuration`
        attribute of a base class will just be overridden by the child class
        in the case that the base class's definition of `configuration` is
        invalid.
        """
        def is_valid_configuration(value):
            # Note: This will exclude `configuration` attributes defined with
            # an @property - which is desired.
            if value is None or not utils.is_iterable(value):
                return False
            elif any([not isinstance(c, (Config, dict)) for c in value]):
                # If there are instances of :obj:`Config` in the configuration,
                # it is likely that this was an attempt to define a valid
                # configuration but the configuration was invalid - so we should
                # log.
                if any([isinstance(c, Config) for c in value]):
                    utils.stdout.log(
                        "Detected a configuration definition for class {name} "
                        "that is invalid.  The configuration will be ignored."
                    )
                return False
            return True

        configuration_sets = []
        for base in bases:
            configuration = getattr(base, 'configuration', None)
            # If the base class is explicitly defined to not be configurable,
            # simply do not configurations.
            if configuration is NotConfigurable:
                continue
            # If the base class defines a configuration but it is invalid, do
            # not raise an exception - simply ignore it.
            if not is_valid_configuration(configuration):
                continue
            # This should not raise an exception as we only call this method
            # if the configuration is valid.  The configuration  is not
            # guaranteed to be standardized if the base class does not extend
            # Configurable or leverage ConfigurableMetaClass.
            configuration = standardize_configurations(configuration)
            # Add the configuration set to the overall configuration sets for
            # each base class.
            configuration_sets.append(configuration)
        return configuration_sets

    @classmethod
    def get_current_configurations(cls, dct):
        """
        Determines the set of individual :obj:`Config` instances defined on
        the child class, not accounting for the individual :obj:`Config`
        instances defined on any base class.
        """
        configuration = dct.get('configuration', None)
        if configuration is None:
            return ConfigurationNotSpecified
        elif not utils.is_iterable(configuration):
            raise exceptions.InvalidParamError(
                valid_types=(list, tuple),
                value=configuration,
                param='configurations'
            )
        elif configuration is NotConfigurable:
            return configuration
        # Note: This will raise an exception if the `configuration` is
        # defined with an @property.
        return standardize_configurations(configuration)

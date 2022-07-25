import contextlib
import inspect

from git_blame_project import utils, exceptions

from .decorators import ensure_configurability, ensure_bound, ensure_configured
from .exceptions import (
    ConfigRequiredError, ConfigInvalidError, NotConfiguredError)


# A decorator that is applied to methods or properties that ensures that the
# :obj:`Config` instance is in the process of being configured before allowing
# the property to be accessed or method to be called.
ensure_configuring = exceptions.check_instance(
    exc_cls=TypeError,
    exc_message=lambda instance: (
        f"The configuration {instance.param} cannot be set externally outside "
        "the context of instance configuration."
    ),
    criteria=[
        exceptions.Criteria(attr='__configuring__', default_value=False)
    ]
)


class should_default:
    """
    A placeholder value for the `value` of the :obj:`Config` instance that
    indicates that the default value that the instance is configured with
    accessing the property associated with the :obj:`Config` instance via the
    `__get__` method.
    """


class not_set:
    """
    A placeholder value for the `value` of the :obj:`Config` instance that
    indicates that the value has not yet been set.

    The value on the :obj:`Config` instance will only be of this type up
    until the point in which the :obj:`Config` instance is configured or the
    the :obj:`Config` instance is bound and the static class it is bound to
    defines the value.
    """


class not_provided:
    """
    A placeholder value that indicates that the value associated with the
    parameter of the :obj:`Config` instance was not provided during the
    configuration of the :obj:`Config` instance.
    """


class do_not_set:
    """
    A placeholder value that indicates that the value associated with the
    parameter of the :obj:`Config` instance that was provided during
    configuration of the :obj:`Config` instance should not be set on the
    :obj:`Config` instance.
    """


class Config(exceptions.FormattableModelMixin):
    """
    A descriptor that represents a single attribute of a configurable class
    and certain configurations for how that attribute should be treated when
    it is set or accessed on the configurable class or instance.

    The configuration of the :obj:`Config` instance allows the attribute of
    the configurable class or instance to exhibit the following behavior:

    (1) A default value can be used for the attribute in the case that it is
        not provided or null when the instance is configured.

    (2) Validation of the value can be performed when the configurable instance
        is configured with the value or the attribute is set directly on the
        configurable instance.

    (3) Formatting of the value can be performed when accessing the attribute on
        on the configurable instance.
    """
    def __init__(self, *args, **kwargs):
        # The class can be provided on initialization if the Config instance
        # should be immediately bound to the provided class.
        klass = kwargs.pop('klass', None)
        if klass is not None:
            self._klass = None
            self.klass = klass

        # Keep track of whether or not the Config instance was configured.
        self._was_configured = False

        # Keep track of whether or not the value of the Config instance was set
        # from the bound static class.
        self._set_statically = False

        self._args = list(args)
        self._kwargs = kwargs
        exceptions.FormattableModelMixin.__init__(self, **kwargs)

    def bind(self, klass):
        """
        Associates the :obj:`Config` instance with the class that defines it
        and marks the :obj:`Config` instance as having been bound.

        Note that a :obj:`Config` instance can be bound multiple times, each
        time to a different class.  Each time the :obj:`Config` instance is
        rebound, it will have its internal value reset.
        """
        self.klass = klass

    @ensure_configurability
    def configure(self, instance, config=None):
        """
        Configures the value of the :obj:`Config` instance based on a provided
        set of configuration values.

        Parameters:
        ----------
        instance: :obj:`object`
            The configurable instance that the :obj:`Config` instance is
            associated with.

        config: :obj:`dict` or :obj:`object` or :obj:`type` (optional)
            A set of configuration values that the parameter associated with
            this :obj:`Config` instance will be read from.

            If provided as an :obj:`dict`, the value will be read via a key
            lookup on the :obj:`dict` instance.  If provided as a class or
            class instance, the value will be read via attribute lookup on
            the class or class instance.

            If not provided, the value will be treated as not existing in
            the configuration, which is a case that will be handled further
            downstream when the value is being set on this :obj:`Config`
            descriptor.

            Default: None
        """
        with self.configuring_context():
            self._configure(instance, config)

    def _configure(self, instance, config=None):
        value = self.read(config)
        self.__set__(instance, value)

    def read(self, config=None):
        """
        Reads the value associated with the `param` of this :obj:`Config`
        instance from the optionally provided set of configuration values,
        provided either as a :obj:`dict` mapping of configuration parameters
        to values or an instance or class that defines the configuration
        parameters as attributes.

        Parameters:
        ----------
        config: :obj:`dict` or :obj:`object` or :obj:`type` (optional)
            The set of configuration values that the parameter associated with
            this :obj:`Config` instance will be read from.

            If provided as an :obj:`dict`, the value will be read via a key
            lookup on the :obj:`dict` instance.  If provided as a class or
            class instance, the value will be read via attribute lookup on
            the class or class instance.

            If not provided, the value will be treated as not existing in
            the configuration, which is a case that will be handled further
            downstream when the value is being set on this :obj:`Config`
            descriptor.

            Default: None
        """
        if config is not None:
            if isinstance(config, dict):
                return config.get(self.accessor, not_provided)
            return getattr(config, self.accessor, not_provided)
        return not_provided

    def raise_null(self):
        raise ConfigInvalidError(
            param=self.param,
            message=(
                "The param {humanized_param} is not allowed to be null."
            )
        )

    def raise_required(self):
        raise ConfigRequiredError(param=self.accessor, klass=self.klass)

    @contextlib.contextmanager
    def configuring_context(self):
        """
        A context manager that indicates that the :obj:`Config` instance is
        in the process of being configured when certain actions are being
        performed.

        This is primarily used to prevent the attribute that this :obj:`Config`
        descriptor is associated with from being manually set outside of a
        configure method.

        Example:
        -------
        For the following example, consider the following configurable class:

        >>> class MyObject(Configurable):
        >>>     configuration = [Config(param='foo')]

        This context manager is meant to prevent the `foo` attribute from being
        set directly on the instance:

        >>> o = MyObject()
        >>> o.foo = 'bar'

        Instead, the correct way to establish the value of `foo` on the
        :obj:`MyObject` instance is as follows:

        >>> o = MyObject()
        >>> o.configure({'foo': 'bar'})
        """
        try:
            setattr(self, '__configuring__', True)
            yield self
        finally:
            setattr(self, '__configuring__', False)
            self._was_configured = True

    def can_reconfigure(self):
        return getattr(self.klass, 'reconfigurable', False)

    @ensure_bound(is_property=True)
    def klass(self):
        return self._klass

    @klass.setter
    def klass(self, value):
        self._klass = value

        # Keep track of the internal value of the Config instance.
        self._value = not_set

        # When binding the class with the :obj:`Config` instance, if the value
        # associated with the param of this :obj:`Config` instance already
        # exists statically on the class, we need to initialize the value of
        # this :obj:`Config` instance *only in the case that it is not an
        # @property*.  If the value is an @property, we cannot access the value
        # from the class (only the instance) - so the value will be accessed
        # dynamically in the __get__ method.
        existing_value = getattr(self._klass, self.param, not_provided)
        if existing_value is not not_provided:
            if not isinstance(existing_value, property):
                self.force_set_from_klass(existing_value)
            else:
                # Store the original attribute defined as an @property such that
                # it can be returned when attempting to access the parameter
                # associated with this :obj:`Config` instance on the static
                # class.
                self._class_property = getattr(value, self.param, None)

    @property
    def is_bound(self):
        return hasattr(self, '_klass')

    @property
    def was_configured(self):
        return self._was_configured

    @ensure_configured(is_property=True)
    def was_defaulted(self):
        return self._value is should_default

    @property
    def default_provided(self):
        return self.default is not utils.empty

    @ensure_bound(is_property=True)
    def can_configure(self):
        return self.was_configured is False or self.can_reconfigure

    @property
    def param(self):
        """
        Returns the attribute name that this :obj:`Config` instance is
        associated with.  The :obj:`Config` instance will be set on the
        configurable class under this attribute name.
        """
        if len(self._args) == 1 and isinstance(self._args[0], str):
            return self._args[0]
        elif 'param' not in self._kwargs:
            raise exceptions.RequiredParamError(
                param='param',
                klass=self.__class__,
            )
        return self._kwargs['param']

    @property
    def required(self):
        """
        Returns whether or not the parameter associated with this :obj:`Config`
        instance is required when configuring the configurable instance that
        is associated with this :obj:`Config` instance.

        If True and the value is not provided during the configuration of the
        :obj:`Config` instance, the :obj:`ConfigRequiredError` exception will be
        raised.
        """
        return self._kwargs.get('required', False)

    @property
    def allow_null(self):
        """
        Returns whether or not the value that the :obj:`Config` instance is
        configured with is allowed to be null.  If False and a null value is
        provided to the :obj:`Config` instance during configuration, the
        :obj:`ConfigInvalidError` exception will be raised.
        """
        return self._kwargs.get('allow_null', False)

    @property
    def valid_types(self):
        """
        Returns the valid types that the value that the :obj:`Config` instance
        is configured with is allowed to be of.  If provided and the value
        provided to the :obj:`Config` instance during configuration is not
        of the provided types, the :obj:`ConfigInvalidError` exception will be
        raised.
        """
        valid_types = self._kwargs.get('valid_types', None)
        if valid_types is not None:
            return utils.ensure_iterable(valid_types, cast=tuple)
        return None

    @property
    def accessor(self):
        """
        Returns the name of the attribute that is used to read the associated
        configuration value from the provided set of configuration values.

        This is only applicable in cases where the attribute that the
        :obj:`Config` instance is set as on the configurable class it is
        associated with differs from the attribute that the value will exist
        under on the set of configuration values provided during configuration
        of the :obj:`Config` instance.
        """
        return self._kwargs.get('accessor', self.param)

    @property
    def default(self):
        """
        Returns the default value that should be used for the :obj:`Config`
        instance in the case that the value is not provided or null during the
        configuration of the :obj:`Config` instance.

        The default value can either be a value or a callback function, which
        either takes 0 arguments or the instance being configured as its only
        argument.
        """
        return self._kwargs.get('default', utils.empty)

    @property
    def validator(self):
        return utils.ensure_iterable(self._kwargs.get('validate', None))

    def validate(self, value):
        """
        Validates the provided value based on the both the optionally provided
        `validate` parameter and the `valid_types` parameter that the
        :obj:`Config` instance was configured with.
        """
        if self.validator is not None:
            for v in self.validator:
                result = v(value)
                if result is False or isinstance(result, str):
                    raise ConfigInvalidError(
                        param=self.param,
                        value=value,
                        detail=result if isinstance(result, str) else None
                    )
        if self.valid_types is not None \
                and not isinstance(value, self.valid_types) \
                and (value is not None and self.allow_null is True):
            raise ConfigInvalidError(
                param=self.param,
                valid_types=self.valid_types,
                value=value
            )
        return value

    def default_value(self, instance):
        """
        Returns the default value that should be used for the :obj:`Config`
        instance in the case that the value is not provided or is provided as
        a null value during configuration of the :obj:`Config` instance.
        """
        if utils.is_function(self.default):
            argspec = inspect.getfullargspec(self.default)
            if len(argspec.args) == 0:
                return self.default()
            elif len(argspec.args) == 1:
                return self.default(instance)
            raise exceptions.InvalidParamError(
                param='default',
                message=(
                    "If provided as a callable, the {humanized_param} parameter "
                    "must take 0 or 1 argument(s)."
                )
            )
        return self.default

    def __get__(self, obj, objtype=None):
        """
        Accesses the value associated with the param of this :obj:`Config`
        instance on the provided instance or class, uses the default value if
        it is warranted and then returns the formatted value if it is warranted.

        Note:
        ----
        When accessing the attribute associated with the param of this
        :obj:`Config` instance on a static class, the `obj` will be None but
        the `objtype` will be provided:

        >>> class MyObject(Configurable):
        >>>     detail = "Detail"
        >>>     ...
        >>> MyException.detail

        When accessing the attribute associated with the param of this
        :obj:`Config` instance on a class instance, the `obj` will be defined
        but the `objtype` will not be provided:

        >>> class MyObject(Configurable):
        >>>     detail = "Detail"
        >>>     ...
        >>> obj = MyObject(detail="Another detail")
        >>> obj.detail
        """
        def handle_set_instance_value(v):
            if v is should_default:
                # If the defaulted value is None, the :obj:`ConfigInvalidError`
                # would not have been raised when the value was set, so we must
                # do that here.
                v = self.default_value(obj)
                if v is None and not self.allow_null:
                    self.raise_null()
            return self.format(v)

        value = self._value
        if obj is not None:
            # Here, we are accessing the attribute associated with the param
            # of this :obj:`Config` instance on a class instance.
            if value is not_set:
                # If the instance was not yet configured (which means the value
                # is :obj:`not_set`) but the class defines the attribute via
                # an @property, we should use that value.
                if getattr(self, '_class_property', None) is not None:
                    class_property = self._class_property
                    value = class_property.fget(obj)
                    value = self.handle_provided_set_value(value)
                else:
                    raise NotConfiguredError(param=self.param)
            return handle_set_instance_value(value)

        # If we are accessing the value from the static class, the value will
        # not be :obj:`not_set` if it was defined as a static attribute on the
        # class (but not with an @property).
        elif value is not not_set:
            # If the value was defaulted, the default value cannot be determined
            # until the attribute is accessed from the class instance.  This is
            # because the default may be a callable that takes the current
            # instance as an argument.  In this case, we just return the
            # original value set on the class without the default applied.
            if value is should_default:
                # When the value is set from the static class, it will always
                # have a present value (since it is only set in the case that
                # the value is defined on the class).  This means that the
                # original value must have been `None`, because defaults are
                # only ever used if the original provided value is None or
                # not provided.
                value = None
            # If the value is None, then the :obj:`Config` instance must have
            # been configured with `allow_null`.
            elif value is None:
                assert self.allow_null, \
                    "Detected null value when null values are not allowed."
            return self.format(value)
        # If we are accessing the value from the static class, the value will
        # be :obj:`not_set` if it was not defined statically on the class or it
        # was defined with an @property.  If it was defined with an @property,
        # that property will have been stored under the `_class_property`
        # attribute when the :obj:`Config` instance was bound.
        elif getattr(self, '_class_property', None) is not None:
            return getattr(self, '_class_property')

        raise AttributeError(
            f"The attribute {self.param} does not exist on the "
            f"{utils.obj_name(objtype)} instance."
        )

    @ensure_bound
    def force_set(self, instance, value):
        with self.configuring_context():
            self.__set__(instance, value)

    @ensure_bound
    def force_set_from_klass(self, value):
        with self.configuring_context():
            self.set_from_klass(value)

    @ensure_bound
    @ensure_configuring
    def set_from_klass(self, value):
        """
        Sets the value on the :obj:`Config` instance based on a statically
        defined attribute on the class it is bound to.
        """
        if value is None:
            self._value = self.setting_value_when_null
            # if self._value is not should_default:
            self._value = self.validate(self._value)
        else:
            self._value = self.validate(value)
        self._set_statically = True

    @property
    def setting_value_when_not_provided(self):
        # If the value is not provided but it was either already defined
        # statically from the class or the :obj:`Config` instance was
        # already configured, simply do not set it.
        if self._set_statically or self.was_configured:
            if self.was_configured:
                # This should not happen as the value is being set from the
                # configure method and the Config instance should not allow this
                # if it was already configured and cannot reconfigure.  If we
                # were to allow configured values to be set externally, outside
                # of a configure method, we would need to raise an appropriate
                # exception here.
                assert self.can_reconfigure, \
                    f"The Config instance {self} is reconfiguring when it is " \
                    "not allowed to."
            return do_not_set
        # If the value is not provided but a default value was provided, use
        # the default.
        elif self.default_provided:
            return should_default
        # If the value was not provided but the :obj:`Config` instance is
        # required, raise an exception indicating as such.
        elif self.required:
            self.raise_required()
        # If the value was not provided and it is not required, does not have
        # a default and was not already set - we still cannot set it, and an
        # exception will be raised when trying to access the value.
        return do_not_set

    @property
    def setting_value_when_null(self):
        # If the value is null but the :obj:`Config` instance allows null values,
        # set the value as None.
        if self.allow_null:
            return None
        # If the value is null but a default was provided, use the default value.
        elif self.default_provided:
            return should_default
        # If the value was null, null values are not allowed and a default was
        # not provided, we have to raise an exception indicating as such.
        raise ConfigInvalidError(
            param=self.param,
            message=(
                "The param {humanized_param} is not allowed to be null."
            )
        )

    def handle_provided_set_value(self, v):
        if v is None:
            v = self.setting_value_when_null
        # The value should be validated regardless of whether or not the default
        # was used.
        return self.validate(v)

    @ensure_bound
    @ensure_configuring
    def __set__(self, instance, value):
        """
        Validates the provided value associated with the `param` of this
        :obj:`Config` instance and then sets it on the instance.
        """
        # The instance will only ever be a class when the value is being
        # initially set when the :obj:`Config` instance is being bound to a
        # class.  In this case, the `set_from_klass` method is used instead.
        if inspect.isclass(instance):
            raise TypeError(
                f"Configuration {self.param} cannot be set from a static type.")

        if value is not_provided:
            value = self.setting_value_when_not_provided
            if value is do_not_set:
                return

        self._value = self.handle_provided_set_value(value)

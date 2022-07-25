from git_blame_project import utils, exceptions


class ConfigError(exceptions.ParamError):
    prefix = None
    content = [
        "There was a configuration error.",
        "There was an error with config {humanized_param}."
    ]

    def __init__(self, *args, **kwargs):
        from .config import Config
        if len(args) == 1 and isinstance(args[0], Config):
            kwargs['param'] = args[0].param
            super().__init__(*tuple(args[1:]), **kwargs)

        config = kwargs.pop('config', None)
        if config is not None:
            kwargs['param'] = config.param
        super().__init__(*args, **kwargs)


class ConfigLookupError(ConfigError):
    required_on_init = ['param']
    content = [
        "The config {humanized_param} does not exist in the "
        "configuration set."
    ]


class CannotReconfigureError(ConfigError):
    """
    Raised when trying to configure a :obj:`Config` instance or a
    :obj:`Configuration` instance that cannot be configured either because it
    had already been configured and was set as non-reconfigurable.
    """
    content = [
        "The configuration was already configured and cannot be reconfigured.",
        "The config {humanized_param} was already configured."
    ]


class CannotConfigureError(ConfigError):
    """
    Raised when trying to access a property or or method on an instance
    that is in a state that does not support configuration.
    """
    prefix = [
        "Cannot configure instance.",
        "Cannot configure {klass} instance."
    ]
    content = (
        "The instance {klass} is in a state that does not allow "
        "configuration."
    )
    required_on_init = ['klass']


class NotConfiguredError(ConfigError):
    """
    Raised when trying to access a method or property of a :obj:`Config`
    instance or a :obj:`Configuration` instance that requires that the
    instance was configured.
    """
    content = [
        "The configuration has not yet been configured.",
        "The config {humanized_param} was not yet configured."
    ]


class ConfiguredError(ConfigError):
    """
    Raised when trying to access a method or property of a :obj:`Config`
    instance or a :obj:`Configuration` instance that requires that the
    instance was not yet configured.
    """
    content = [
        "The configuration has already been configured.",
        "The config {humanized_param} was already configured."
    ]


class ConfigRequiredError(ConfigError):
    """
    Raised when the value associated with the param of the :obj:`Config`
    instance is not provided but is required.
    """
    content = "The config {humanized_param} is required."
    required_on_init = ['param']


class ConfigInvalidError(ConfigError):
    """
    Raised when the value associated with the param of the :obj:`Config`
    is invalid.  This can occur if the value itself is invalid or if the
    value is an iterable that contains invalid values.

    Parameters:
    ----------
    Like all attributes of the :obj:`AbstractException` class and its
    extensions, each attribute can be provided on initialization, defined
    statically on the class as a simple attribute or defined statically
    on the class as an @property.

    In all cases, the :obj:`ExceptionMetaClass` will be used to wrap the
    attribute in an @property to ensure it is retrieved from the correct
    source (initialization arguments or static class attributes) and
    formatted when accessed.

    value: (optional)
        A single value that was invalid and associated with the parameter that
        was provided to the exception class.

        Default: None

    valid_types: :obj:`type` or :obj:`tuple` or :obj:`list` (optional)
        Either a single type or several types of which the parameter was
        expected to be of.

        Default: None
    """
    attributes = [
        exceptions.ExceptionAttribute(name='value'),
        exceptions.ExceptionAttribute(
            name='valid_types',
            formatter=utils.ensure_iterable
        ),
    ]

    content = [
        "Received invalid value {value}.",
        "Received invalid value {value} for config {humanized_param}.",
        "Received invalid value for config {humanized_param}, "
        "expected values of type {humanized_valid_types}.",
        "Received invalid value {value} for config {humanized_param}, "
        "expected values of type {humanized_valid_types}.",
    ]

    @property
    def humanized_valid_types(self):
        return utils.humanize_list(self.valid_types, conjunction="or")


class ConfigBoundError(ConfigError):
    """
    Raised when accessing an attribute on an bound :obj:`Config` instance
    requires that the :obj:`Config` instance is unbound.
    """
    content = [
        "The configuration is already bound.",
        "The config {humanized_param} is already bound."
    ]


class ConfigNotBoundError(ConfigError):
    """
    Raised when accessing an attribute on an unbound :obj:`Config` instance
    requires that the :obj:`Config` instance is bound.
    """
    content = [
        "The configuration is not bound.",
        "The config {humanized_param} is not bound."
    ]

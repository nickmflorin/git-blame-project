from git_blame_project import exceptions, utils


NON_CONFIGURABLE_VALUES = (None, False)


class NotConfigurable:
    """
    A placeholder value that is used to indicate that a class is not
    configurable even though it uses the :obj:`ConfigurableMetaClass`.

    This is used in situations where a child class may extend a parent class
    that extends :obj:`Configurable`, and it is desired that the child class
    not be configurable even though the parent is.
    """


class ConfigurationNotSpecified:
    """
    A placeholder value that is used to indicate that a class does not specify
    a configuration.  This means that the `configuration` attribute is either
    not set on the class, is None or is an empty iterable.

    In this case, the class will still be treated as configurable if it
    inherits configurations from parent classes.  Otherwise, it will not be
    treated as configurable.
    """


def standardize_configurations(configuration):
    from .config import Config
    assert utils.is_iterable(configuration), \
        "The configuration must be an iterable."
    invalid_configurations = []
    standardized = []
    for c in configuration:
        if isinstance(c, Config):
            standardized.append(c)
        elif isinstance(c, dict):
            standardized.append(Config(**c))
        else:
            invalid_configurations.append(c)
    if invalid_configurations:
        raise exceptions.InvalidParamError(
            param='configurations',
            valid_types=(Config, dict),
            value=invalid_configurations
        )
    return standardized

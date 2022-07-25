from git_blame_project import utils
from .meta import ConfigurableMetaClass


__all__ = (
    'configurable',
    'Configurable'
)


class Configurable(metaclass=ConfigurableMetaClass):
    """
    An abstract class that represents an object that can be configured.
    """
    def __init__(self, **kwargs):
        # Even though any class extending :obj:`Configurable` will leverage the
        # :obj:`ConfigurableMetaClass`, it will not have the properties and
        # behaviors of a configurable class if the `configuration` attribute is
        # not defined, inherited or set as NotConfigurable.  In this case,
        # the instance will not have a `configure` method.
        if self.is_configurable \
                and getattr(self, 'configure_on_init', False) is True:
            config = kwargs.pop('config', utils.empty)
            if config is utils.empty:
                config = {}
                for conf in self.configuration:
                    if conf.param in kwargs:
                        config[conf.param] = kwargs[conf.param]

            if config is not utils.empty:
                self.configure(config, strict=False)


def configurable(cls):
    return cls

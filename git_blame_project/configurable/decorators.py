from git_blame_project import exceptions

from .exceptions import (
    ConfigNotBoundError, NotConfiguredError, ConfiguredError,
    CannotReconfigureError, CannotConfigureError)


ensure_bound = exceptions.check_instance(
    exc_cls=ConfigNotBoundError,
    exc_kwargs=lambda instance: {"param": instance.param, 'klass': instance},
    criteria=[
        exceptions.Criteria(attr='is_bound')
    ]
)

ensure_configured = exceptions.check_instance(
    exc_cls=NotConfiguredError,
    exc_kwargs=lambda instance: {"param": instance.param, 'klass': instance},
    criteria=[
        exceptions.Criteria(attr='was_configured')
    ]
)

ensure_reconfigurable = exceptions.check_instance(
    exc_cls=CannotReconfigureError,
    exc_kwargs=lambda instance: {"param": instance.param, 'klass': instance},
    criteria=[
        exceptions.Criteria(attr='can_reconfigure')
    ]
)

ensure_unconfigured = exceptions.check_instance(
    exc_cls=ConfiguredError,
    exc_kwargs=lambda instance: {"param": instance.param, 'klass': instance},
    criteria=[
        exceptions.Criteria(attr='was_configured', value=False)
    ]
)


def exception_kwargs(instance):
    from .config import Config
    if isinstance(instance, Config):
        return {"param": instance.param, 'klass': instance}
    return {'klass': instance}


ensure_configurability = exceptions.check_instance(
    exc_cls=CannotConfigureError,
    exc_kwargs=exception_kwargs,
    criteria=[
        # Note: If there are no configurations specified, the class will not
        # have the configure method attached to it.
        exceptions.Criteria(
            func=lambda instance: getattr(instance, 'can_configure', True),
        )
    ]
)

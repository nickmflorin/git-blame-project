from git_blame_project import utils

from .base import AbstractException
from .exceptions import InvalidParamError, RequiredParamError
from .models import ExcParams


class Criteria(ExcParams):
    """
    Defines the criteria that is used to evaluate whether or not the instance
    is in a state that should allow the decorated method to be called or the
    decorated property to be accessed.

    Parameters:
    ----------
    func: :obj:`lambda` (optional)
        The conditional function that will be used to determine whether or not
        the instance is in a state that should allow the decorated method to be
        called or the decorated property to be accessed.

        Used in cases where simply checking the value of an attribute (defined
        by the `attr` parameter) is not sufficient enough to make the
        determination.

        The function should take the instance being evaluated as its first
        and only argument.  Additionally, it should return a boolean or a
        string message.  If the returned value is False or a string, the
        instance will be treated as though it is not in a state that should
        allow the decorated content to be accessed.  If the returned value is
        a string, that string will be used as the message in the raised
        exception.

        Required if the `attr` parameter is not provided.

        Default: None

    attr: :obj:`str` (optional)
        The attribute name on an instance being evaluated in cases where the
        evaluation of whether or not the instance is in a state that should
        allow the decorated method to be called or the decorated property to be
        accessed is as simple as evaluating the value of this attribute on the
        instance.

        Required if the `func` parameter is not provided.

        Default: None

    value (optional)
        The value associated with the `attr` parameter on the instance that
        should allow the decorated content to be accessed.

        In other words, if the `attr` parameter is `foo` and the `value`
        parameter is `"bar"`, then an exception will be raised if `instance.foo`
        does not equal `"bar"`.

        Default: True

    default_value (optional)
        The value that should be used in the case that the provided `attr` does
        not exist on the instance.

        This should only be used in cases where the `attr` is provided and is
        not guaranteed to exist on the instance.  In this case, the attribute
        lookup will be treated more flexibly and the default value will be
        used if the attribute lookup fails (instead of raising an
        :obj:`AttributeError`).

        Default: None
    """
    def __init__(self, **kwargs):
        self._func = kwargs.pop('func', None)
        self._attr = kwargs.pop('attr', None)
        self._value = kwargs.pop('value', True)
        self._default_value = kwargs.pop('default_value', utils.empty)

        if self._func is None and self._attr is None:
            raise RequiredParamError(
                param=['func', 'attr'],
                conjunction='or',
                klass=self.__class__
            )
        super().__init__(**kwargs)

    def __call__(self, instance, strict=True):
        # If the evaluation function is provided explicitly to the instance,
        # perform the evaluation using that function.
        if self._func is not None:
            result = self._func(instance)
            if result is False or isinstance(result, str):
                return self.failed(
                    instance=instance,
                    strict=strict,
                    message=result if isinstance(result, str) else None
                )
            return True
        # If the evaluation function is not provided explicitly to the instance,
        # the evaluation is done based on comparing the value of the attribute
        # associated with the `attr` parameter to the value associated with the
        # `value` parameter.
        instance_value = self.get_instance_value(instance)
        if self._value != instance_value:
            default_message = (
                f"The value of attribute {self._attr} on the "
                f"{utils.obj_name(instance)} instance does not equal "
                f"{self._value}."
            )
            return self.failed(
                instance=instance,
                strict=strict,
                default_message=default_message
            )
        return True

    def get_instance_value(self, instance):
        if self._default_value is not utils.empty:
            return getattr(instance, self._attr, self._default_value)
        try:
            return getattr(instance, self._attr)
        except AttributeError as e:
            raise InvalidParamError(
                param='attr',
                message=(
                    f'The {utils.obj_name(instance)} does not have an '
                    f'attribute {self._attr}.'
                )
            ) from e

    def failed(self, instance, strict=True, **kwargs):
        if strict:
            self.raise_exception(instance, **kwargs)

    def raise_exception(self, instance, **kwargs):
        exc_cls = self._exc_cls
        if exc_cls is None:
            exc_cls = TypeError
        message = self.exc_message(instance, **kwargs)
        if issubclass(exc_cls, AbstractException):
            exc_kwargs = self.exc_kwargs(instance) or {}
            if message is not None:
                exc_kwargs.update(message=message)
            raise exc_cls(**exc_kwargs)
        raise exc_cls(message)

    def provide_missing_values(self, decorator_factory):
        """
        Sets the provided attributes on the :obj:`Criteria` instance if the
        instance was not originally configured with them but the more general
        :obj:`check_instance` instance was.
        """
        for k in self.attrs:
            v = getattr(decorator_factory, f"_{k}")
            if v is not None and getattr(self, f"_{k}") is None:
                setattr(self, f"_{k}", v)

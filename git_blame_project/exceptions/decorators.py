
import functools

from git_blame_project import utils

from .exceptions import InvalidParamError
from .models import ExcParams


__all__ = ('check_instance', )


class check_instance(ExcParams):
    """
    A decorator factory that returns a decorator - which is configured based on
    the parameters provided to initialize the :obj:`check_instance` instance -
    that is used to ensure certain criteria of a class instance is met before
    allowing the decorated method or property to be accessed.

    If the decorator determines that the criteria defined its configuration is
    not met, an exception will be raised.

    Usage:
    -----
    The decorator that is returned from the :obj:`check_instance` decorator
    factory can be used in a variety of ways.  For example purposes, assume
    that the following decorator is created:

    >>> ensure_valid = check_instance(
    >>>     attr='valid',
    >>>     exc=ObjectInvalid,
    >>>     exc_kwargs=lambda instance: {'name': instance.name}
    >>> )

    When the `ensure_valid` decorator is applied to a class method or property,
    it will ensure that the value of `valid` on the instance is `True` before
    allowing the decorated method to be called or decorated property to be
    accessed.

    The `ensure_valid` decorator can be used in the following ways:

    (1) Decorating a Class Method
        In this example, if the `my_method` method of an instance of
        :obj:`MyObject` is called when the instance is not valid, the
        :obj:`ObjectInvalid` exception will be raised:

        >>> class MyObject:
        >>>     @ensure_valid
        >>>     def my_method(self, foo):
        >>>         ....

    (2) Decorating a Class Property
        In this example, if the `my_property` property of an instance of
        :obj:`MyObject` is accessed when the instance is not valid, the
        :obj:`ObjectInvalid` exception will be raised:

        >>> class MyObject:
        >>>     @ensure_valid(is_property=True)
        >>>     def my_property(self):
        >>>         ....

    (3) Manual Usage
        The `ensure_valid` decorator can also be manually used by providing
        the class instance as the first argument to the call.  In this case,
        the `ensure_valid` decorator will behave as a function, and ensure
        that the instance provided as its argument meets the criteria based
        on its configuration.

        >>> class MyObject:
        >>>     ...
        >>>
        >>> o = MyObject()
        >>> ensure_valid(o)

    Parameters:
    ----------
    criteria: :obj:`list` or :obj:`tuple` or :obj:`Criteria` (optional)
        Either a single :obj:`Criteria` instance or an iterable of
        :obj:`Criteria` instances that define the conditions that must be met
        for the decorator to allow access to the decorated content.

        This parameter should be used when the simple combination of the
        `attr` parameter and `value` parameter do not suffice to define the
        criteria that the instance must meet.

        If not provided, the `attr` parameter must be provided - otherwise,
        there is no way to form the criteria that a given instance must meet.

        Default: None
    """
    def __init__(self, *criteria, **kwargs):
        if 'criteria' in kwargs:
            self._criteria = kwargs.pop('criteria')
        else:
            self._criteria = utils.iterable_from_args(criteria)
        if len(self._criteria) == 0:
            raise InvalidParamError(
                param='criteria',
                message='At least 1 criteria must be provided.'
            )
        super().__init__(**kwargs)

    def __call__(self, *args, **kwargs):
        # If the first and only argument is a function, then the instance is
        # being used as a decorator:
        if len(args) == 1 and utils.is_function(args[0]):
            return self.inner_factory(args[0])
        # If the first and only argument is a class instance, then the instance
        # is being called manually:
        elif len(args) == 1 and isinstance(args[0], object):
            return self.evaluate(args[0], **kwargs)
        # If the function to decorate or instance is not provided as an argument,
        # then the decorator is being used with arguments - which means we have
        # to return the entire decorator.
        return self.decorator_factory(**kwargs)

    def evaluate(self, instance, strict=True):
        """
        Evaluates whether or not the provided instance meets the criteria
        defined by the :obj:`Criteria` instances associated with the decorator.

        If a given criteria is not met, the exception defined by the
        configuration of the individual :obj:`Criteria` instance combined with
        the configuration of the :obj:`check_instance` decorator factory will
        be raised (in strict mode) or the value of None will be returned
        (in non-strict mode).

        Parameters:
        ----------
        instance: :obj:`object`
            The instance that the method or property being decorated belongs
            to.

        strict: :obj:`bool` (optional)
            Whether or not the exception should be raised in the case that the
            criteria is not met.  If `False`, the value `None` will be returned
            in the case the criteria is not met.

            Default: True
        """
        for c in self._criteria:
            # If any parameters are specified more generally as configurations
            # to the :obj:`check_instance` decorator factory, but not provided
            # to the individual :obj:`Criteria` instance, set them on the
            # :obj:`Criteria` instance.
            c.provide_missing_values(self)
            result = c(instance, strict=strict)
            if result is not True:
                return result
        return True

    def inner_factory(self, func, is_property=False):
        @functools.wraps(func)
        def inner(instance, *a, **kw):
            strict = kw.pop('strict', True)
            result = self.evaluate(instance, strict=strict)
            # If the evaluation fails, either an exception will be raised or
            # None will be returned.  If it succeeds, True will be returned.
            if result is not True:
                return None
            return func(instance, *a, **kw)
        if is_property:
            return property(inner)
        return inner

    def decorator_factory(self, **kw):
        is_property = kw.pop('is_property', False)

        def decorator(func):
            return self.inner_factory(func, is_property=is_property)
        return decorator

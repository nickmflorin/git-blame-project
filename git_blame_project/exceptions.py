import collections
import functools
from .utils import (
    obj_name, humanize_list, ensure_iterable, cjoin, empty, pluck_first_kwarg)


RegistrationInstruction = collections.namedtuple(
    'RegistrationInstruction',
    ['cls', 'param', 'kwargs']
)


def ignore_null_values(func):
    @functools.wraps(func)
    def decorated(instance, obj, value):
        if value is None:
            return value
        return func(instance, obj, value)
    return decorated


class Registration:
    def __init__(self, cls, param):
        self._param = param
        self._cls = cls
        self._original = getattr(cls, self._param, None)
        self._value = empty

    @property
    def param(self):
        return self._param

    @classmethod
    def lazy_init(cls, param, kwargs=None):
        kwargs = kwargs = {}

        def instantiator(klass):
            return cls(klass, param, **kwargs)
        return instantiator

    def validate(self, obj, value):
        return value

    def format(self, obj, value):
        return value

    def get_obj_value(self, obj):
        if self._value is not empty:
            # In the case that the `_value` attribute was set on the Registration
            # class, the `__set__` method of this Registration class was called
            # and the value was validated before it was set - so we do not need
            # to revalidate the value.
            return self.format(obj, self._value)
        elif self._original is not None:
            # In the case that the value exists statically on the Exception
            # class and is not an @property, the ExceptionMetaClass will have
            # validated the value manually when the class was created - so we
            # do not need to revalidate the value.
            if not isinstance(self._original, property):
                return self.format(obj, self._original)
            # In the case that the value exists statically on the Exception
            # class but is an @property, the value will not have been validated
            # as it was not set via the `__set__` method on this Registration
            # class and was not validated manually in the ExceptionMetaClass
            # when the class was created - so we have to validate the value
            # on retrieval.
            value = self.validate(obj, self._original.fget(obj))
            return self.format(obj, value)
        raise AttributeError(
            f"The attribute {self.param} does not exist on the {obj.__class__} "
            "instance."
        )

    def __get__(self, obj, objtype=None):
        if obj is not None:
            return self.get_obj_value(obj)
        elif self._original is not None:
            if isinstance(self._original, property):
                # Here, we are returning the @property instance.
                return self._original.__get__(obj, objtype)
            # Here, the value exists statically on the Exception class and
            # is not an @property - the ExceptionMetaClass will have
            # validated the value manually when the class was created - so we
            # do not need to revalidate the value.
            return self._original
        raise AttributeError(
            f"The attribute {self.param} does not exist on the {obj} "
            "instance."
        )

    def __set__(self, instance, value):
        if hasattr(instance.__class__, self.param) and value is None:
            return
        self._value = self.validate(instance, value)


class StringRegistration(Registration):
    @ignore_null_values
    def validate(self, obj, value):
        if not isinstance(value, str):
            raise ImproperInitializationError(obj, message=(
                f"Expected a string type for `{self.param}` parameter, but "
                f"received {type(value)}."
            ))
        return value

    @ignore_null_values
    def format(self, obj, value):
        return value.strip()


class ObjectNameRegistration(Registration):
    @ignore_null_values
    def validate(self, obj, value):
        if not isinstance(value, (object, type)):
            raise ImproperInitializationError(obj, message=(
                f"Expected a class or instance type for param `{self.param}` "
                f"but received {type(value)}."
            ))
        return value

    @ignore_null_values
    def format(self, obj, value):
        return obj_name(value)


class PrefixRegistration(StringRegistration):
    def __init__(self, cls, param, is_detail=False):
        self._is_detail = is_detail
        super().__init__(cls, param)

    def end_char(self, obj):
        if not self._is_detail and obj.content is None:
            return "."
        # In the case that the detail is None, the entire line will be excluded
        # so we do not need to worry about using a "." at the end of the prefix
        # since the prefix will not be displayed.
        return ":"

    @ignore_null_values
    def format(self, obj, value, end_char=None):
        value = value.strip()
        end_char = end_char or self.end_char(obj)
        if not value.endswith(end_char):
            return f"{value}{end_char}"
        return value


class MultipleStringRegistration(StringRegistration):
    @ignore_null_values
    def validate(self, obj, value):
        if not isinstance(value, (str, list, tuple)):
            raise ImproperInitializationError(obj, message=(
                f"Expected a string, list or tuple type for `{self.param}` "
                f"parameter, but received {type(value)}."
            ))
        elif isinstance(value, (list, tuple)):
            non_string_details = [d for d in value if not isinstance(d, str)]
            if non_string_details:
                non_string_types = set([type(d) for d in non_string_details])
                humanized = humanize_list(non_string_types)
                raise ImproperInitializationError(obj, message=(
                    f"Expected all elements of the iterable for the "
                    f"`{self.param}` param to be a string, but received "
                    f"{humanized}."
                ))
        return ensure_iterable(value)

    @ignore_null_values
    def format(self, obj, value):
        return [v.strip() for v in value]


class DetailPrefixRegistration(MultipleStringRegistration):
    @ignore_null_values
    def format(self, obj, value):
        return [
            PrefixRegistration.format(self, obj, v, end_char=":")
            for v in value
        ]


class ExceptionMetaClass(type):
    registrations = [
        PrefixRegistration.lazy_init(
            param='prefix',
            kwargs={'is_detail': False}
        ),
        DetailPrefixRegistration.lazy_init(param='detail_prefix'),
        MultipleStringRegistration.lazy_init(param='detail'),
        MultipleStringRegistration.lazy_init(param='detail_indent'),
        StringRegistration.lazy_init(param='indent'),
        StringRegistration.lazy_init(param='content'),
        ObjectNameRegistration.lazy_init(param='cls_name')
    ]

    def __new__(cls, name, bases, dct):
        if name != 'AbstractException':
            # We do not allow the `message` attribute to be statically defined
            # on classes that extend the AbstractException base class.
            if 'message' in dct:
                raise TypeError(
                    f"The exception class {name} extends `AbstractException` "
                    "and cannot define the `message` attribute statically."
                )
        klass = super().__new__(cls, name, bases, dct)
        for registration in cls.registrations:
            registration_instance = registration(klass)
            existing_value = getattr(klass, registration_instance.param, None)
            # In the case that the value exists statically on the Exception
            # class but is not an @property, we have to validate the value
            # when the class is being created.
            if existing_value is not None \
                    and not isinstance(existing_value, property):
                registration_instance.__set__(klass, existing_value)
            setattr(klass, registration_instance.param, registration_instance)
        return klass


class AbstractException(Exception, metaclass=ExceptionMetaClass):
    detail_indent = "--> "
    indent = None

    def __init__(self, *args, **kwargs):
        if len(args) not in (0, 1, 2):
            raise ImproperInitializationError(self, message=(
                "Expected 0, 1 or 2 positional arguments, but received "
                f"{len(args)}."
            ))
        if len(args) == 2:
            if isinstance(args[0], str):
                self.content = args[0]
                self.cls_name = args[1]
            elif isinstance(args[1], str):
                self.content = args[1]
                self.cls_name = args[0]
            else:
                raise ImproperInitializationError(self, message=(
                    "Expected both a class or instance type and a message "
                    f"string, but received {type(args[0])} and {type(args[1])}."
                ))
        elif len(args) == 1:
            if isinstance(args[0], str):
                self.content = args[0]
                self.cls_name = pluck_first_kwarg('cls', 'instance', **kwargs)
            else:
                self._cls_name = self.cls_name = args[0]
                self.content = kwargs.pop('message', None)
        else:
            self.cls_name = pluck_first_kwarg('cls', 'instance', **kwargs)
            self.content = kwargs.pop('message', None)

        self.detail = kwargs.pop('detail', None)
        self.detail_prefix = kwargs.pop('detail_prefix', None)
        self.prefix = kwargs.pop('prefix', None)
        self.detail_indent = kwargs.pop('detail_indent', None)
        self.indent = kwargs.pop('indent', None)

        if getattr(self, 'object_required', False) and self.cls_name is None:
            raise TypeError(
                "The object class or instance is required to initialize "
                f"{self.__class__}."
            )

    def get_detail_prefix(self, i):
        if self.detail_prefix is None:
            return None
        try:
            return self.detail_prefix[i]
        except IndexError as e:
            raise ImproperInitializationError(
                instance=self,
                message=(
                    "The exception class contains "
                    f"{len(self.detail)} details but only "
                    f"{len(self.detail_prefix)} prefixes.  They must be "
                    "consistent."
                )
            ) from e

    def get_detail_indent(self, i):
        if self.detail_indent is None:
            return None
        try:
            return self.detail_indent[i]
        except IndexError as e:
            raise ImproperInitializationError(
                instance=self,
                message=(
                    "The exception class contains "
                    f"{len(self.detail)} details but only "
                    f"{len(self.detail_indent)} indents.  They must be "
                    "consistent."
                )
            ) from e

    @property
    def message(self):
        if self.prefix is None and self.content is None:
            raise ImproperInitializationError(
                instance=self,
                message=(
                    f"The exception class {self.__class__} does not define a "
                    "message or a prefix."
                )
            )
        message_components = [cjoin(self.indent, self.prefix, self.content)]
        if self.detail is not None:
            for i, d in enumerate(self.detail):
                detail_prefix = self.get_detail_prefix(i)
                detail_indent = self.get_detail_indent(i)
                message_components.append(cjoin(detail_indent, detail_prefix, d))
        return "\n".join(message_components)

    def __str__(self):
        return self.message


class ImproperInitializationError(AbstractException):
    object_required = True

    @property
    def prefix(self):
        return f"Improper Initialization of {self.cls_name}"


class ImproperUsageError(AbstractException):
    object_required = True

    def __init__(self, *args, **kwargs):
        self._func = kwargs.pop('func', None)
        super().__init__(*args, **kwargs)

    @property
    def func_name(self):
        if self._func is not None:
            return obj_name(self._func)
        return self._func

    @property
    def prefix(self):
        if self._func is not None:
            return (
                f"Improper Usage of Method {self.func_name} "
                f"on {self.cls_name}."
            )
        return f"Improper Usage of {self.cls_name}."


class GitBlameProjectError(AbstractException):
    pass

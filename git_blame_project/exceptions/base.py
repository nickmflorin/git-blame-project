from abc import ABC
import functools
import inspect

from git_blame_project import utils


def processor(func):
    argspec = inspect.getfullargspec(func)

    @functools.wraps(func)
    def decorated(instance, obj, value, **kwargs):
        if value is None:
            return value
        if 'obj' in argspec.args:
            return func(instance, obj, value, **kwargs)
        return func(instance, value, **kwargs)
    return decorated


class Registration(ABC):
    """
    Base class for a descriptor that is used for attributes of the
    :obj:`AbstractException` class that is responsible for the following:

    (1) Validating the value of the property when it the :obj:`AbstractException`
        class is initialized with the property, or validating the value of the
        property when it is defined statically on the :obj:`AbstractException`
        class.

    (2) Formatting the value of the associated property when it is accessed on
        the :obj:`AbstractException` class extension instance.

    This class is abstract and is not meant to be used directly, but only via
    an extension of this class.
    """
    def __init__(self, cls, param):
        self._param = param
        self._cls = cls
        self._original = getattr(cls, self._param, None)
        self._value = utils.empty

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
        # Override to validate values before they are set on the
        # :obj:`AbstractException` instance.
        return value

    def _format(self, obj, value):
        # Define to format and standardize values before they are accessed on
        # the :obj:`AbstractException` instance.
        if hasattr(self, 'format'):
            formatter = getattr(self, 'format')
            return formatter(obj, value)
        return value

    def get_obj_value(self, obj):
        if self._value is not utils.empty:
            # In the case that the `_value` attribute was set on the Registration
            # class, the `__set__` method of this Registration class was called
            # and the value was validated before it was set - so we do not need
            # to revalidate the value.
            return self._format(obj, self._value)
        elif self._original is not None:
            # In the case that the value exists statically on the Exception
            # class and is not an @property, the ExceptionMetaClass will have
            # validated the value manually when the class was created - so we
            # do not need to revalidate the value.
            if not isinstance(self._original, property):
                return self._format(obj, self._original)
            # In the case that the value exists statically on the Exception
            # class but is an @property, the value will not have been validated
            # as it was not set via the `__set__` method on this Registration
            # class and was not validated manually in the ExceptionMetaClass
            # when the class was created - so we have to validate the value
            # on retrieval.
            value = self.validate(obj, self._original.fget(obj))
            return self._format(obj, value)
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
    @processor
    def validate(self, obj, value):
        if not isinstance(value, str):
            raise ImproperInitializationError(obj, message=(
                f"Expected a string type for `{self.param}` parameter, but "
                f"received {type(value)}."
            ))
        return value

    @processor
    def format(self, value):
        return value.strip()


class ObjectNameRegistration(Registration):
    @processor
    def validate(self, obj, value):
        if not isinstance(value, (object, type)):
            raise ImproperInitializationError(obj, message=(
                f"Expected a class or instance type for param `{self.param}` "
                f"but received {type(value)}."
            ))
        return value

    @processor
    def format(self, value):
        return utils.obj_name(value)


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

    @processor
    def format(self, obj, value, end_char=None):
        value = value.strip()
        end_char = end_char or self.end_char(obj)
        if not value.endswith(end_char):
            return f"{value}{end_char}"
        return value


class MultipleStringRegistration(StringRegistration):
    @processor
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
                humanized = utils.humanize_list(non_string_types)
                raise ImproperInitializationError(obj, message=(
                    f"Expected all elements of the iterable for the "
                    f"`{self.param}` param to be a string, but received "
                    f"{humanized}."
                ))
        return utils.ensure_iterable(value)

    @processor
    def format(self, value):
        return [v.strip() for v in value]


class DetailPrefixRegistration(MultipleStringRegistration):
    @processor
    def format(self, obj, value):
        return [
            PrefixRegistration.format(self, obj, v, end_char=":")
            for v in value
        ]


class ExceptionMetaClass(type):
    """
    A Metaclass for the :obj:`AbstractException` class that provides two
    implementations:

    (1) Guarantees that extensions of the :obj:`AbstractException` do not define
        a `message` attribute statically.  This ensures that the formatting
        of all exceptions in the project is consistent and composed of the
        individual attributes of the :obj:`AbstractException` class.

    (2) Replaces attributes that may have been defined statically on the
        :obj:`AbstractException` class with descriptors represented by the
        :obj:`Registration` class.  If the attribute was not defined statically
        on the :obj:`AbstractException` class, the attributes are still added
        to the :obj:`AbstractException` class with these descriptors.

        Ensuring that each attribute of the :obj:`AbstractException` class
        uses the :obj:`Registration` descriptor ensures that all attribute
        values are properly validated and formatted, even in the case they are
        defined with static properties on the :obj:`AbstractException` class
        exception.
    """
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
    """
    Abstract base class for all :obj:`Extension` classes used in this project.
    This :obj:`Extension` class should never be used alone, but only via an
    :obj:`Extension` class that extends it.

    All properties of the :obj:`AbstractException` instance can be provided
    by one of three means (ordered by priority when a property is defined
    by multiple means):

    (1) Statically on the :obj:`AbstractException` class extension.
    (2) Dynamically on the :obj:`AbstractException` class extension via
        @property.
    (3) Dynamically on initialization of the :obj:`AbstractException` class
        extension.

    Each property uses a descriptor, the :obj:`Registration` class, which
    (in conjunction with the :obj:`ExceptionMetaClass` metaclass) is responsible
    for:

    (1) Validating the value of the property when it the :obj:`AbstractException`
        class is initialized with the property, or validating the value of the
        property when it is defined statically on the :obj:`AbstractException`
        class.
    (2) Formatting the value of the associated property when it is accessed on
        the :obj:`AbstractException` class extension instance.

    Parameters:
    ----------
    content: :obj:`str` (optional)
        The exception content refers to the core message the exception will
        display in its string form.  The content is displayed in first line of
        the exception string.

        The message content of the exception class can be defined in a variety
        of ways:

        (1) Statically on the exception class via a `content` @property or
            string with the attribute name `content`.

            >>> class MyCustomException(AbstractException):
            >>>     @property
            >>>     def content(self):
            >>>         return "Main exception message."

        (2) Dynamically on exception initialization via a positional argument
            or a keyword argument `message`.

            >>> class MyCustomException(AbstractException):
            >>>     pass
            >>> exc = MyCustomException(message="Main exception message.")
            >>> exc = MyCustomException("Main exception message.")

        If the `prefix` parameter is not defined or provided, the `content`
        parameter must be defined or provided - otherwise there is no way to
        construct the core exception message.

        Default: None

    prefix: :obj:`str` (optional)
        A :obj:`str` that will be displayed in front of the main exception
        `content` in the string form of the exception instance.

        Like all other attributes of the exception class, the `prefix` attribute
        can be defined statically on the class or on initialization of the
        exception class instance.

        If the `content` parameter is not defined or provided, the `prefix`
        parameter must be defined or provided - otherwise there is no way to
        construct the core exception message.

        Default: None

    indent: :obj:`str` (optional)
        A :obj:`str` that will be displayed in front of the combined message
        `content` and `prefix`.  This will typically be an empty string.

        Like all other attributes of the exception class, the `indent` attribute
        can be defined statically on the class or on initialization of the
        exception class instance.

        Default: None

    cls or instance: A class type or any class instance (optional)
        The class or instance that the exception may be related to - if
        applicable.  This property is only used for extensions of the
        :obj:`AbstractException` class that want to reference it in the
        string form of the exception.

        The cls or instance the exception is related to can be defined in a
        variety of ways:

        (1) Statically on the exception class via a `content` @property or
            string with the attribute name `cls` or `instance`:.

            >>> class MyCustomException(AbstractException):
            >>>     @property
            >>>     def cls(self):
            >>>         return MyCustomObj

        (2) Dynamically on exception initialization via a positional argument
            or a keyword argument `cls` or `instance`:.

            >>> class MyCustomException(AbstractException):
            >>>     pass
            >>> exc = MyCustomException(cls=MyCustomObj)
            >>> exc = MyCustomException("Main exception message.", MyCustomObj)

        Default: None

    detail: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that define
        detailed information to accompany the core exception content.  Each
        detail will be defined on subsequent lines after the core exception
        message in the string form of the exception.

        >>> exc = MyCustomException(
        >>>     message="Core message.",
        >>>     detail=["The value was invalid."],
        >>>     detail_prefix="Detail",
        >>> )
        >>> str(exc)
        >>> "Core message."
        >>> "Detail: The value was invalid."

        Like all other attributes of the exception class, the `detail` attribute
        can be defined statically on the class or on initialization of the
        exception class instance.

        Default: None

    detail_prefix: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that define
        the prefixes that will be shown before each detail in the string form
        of the exception.

        If it is desired that the same prefix be used for all details, it can
        be provided as a simple string.  Otherwise, it can be provided as an
        array to indicate the specific prefixes to use for each detail line.

        Like all other attributes of the exception class, the `detail_prefix`
        attribute can be defined statically on the class or on initialization of
        the exception class instance.

        Default: None

    detail_indent: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that define
        the indents that will be displayed before each combined detail prefix
        and detail line.

        If it is desired that the same indent be used for all details, it can
        be provided as a simple string.  Otherwise, it can be provided as an
        array to indicate the specific indents to use for each detail line.

        Like all other attributes of the exception class, the `detail_indent`
        attribute can be defined statically on the class or on initialization of
        the exception class instance.

        Default: "--> "
    """
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
                self.cls_name = utils.pluck_first_kwarg(
                    'cls', 'instance', **kwargs)
            else:
                self._cls_name = self.cls_name = args[0]
                self.content = kwargs.pop('message', None)
        else:
            self.cls_name = utils.pluck_first_kwarg(
                'cls', 'instance', **kwargs)
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

    def get_detail_attribute(self, i, attr):
        assert attr in ('detail_prefix', 'detail_indent'), \
            f"Invalid detail attribute {attr} provided."

        if getattr(self, attr) is None:
            return None
        try:
            return getattr(self, attr)[i]
        except IndexError as e:
            # If there is only one attribute in the array, it means that it was
            # most likely provided as a single value and it should be used for
            # all details in the array.
            if len(getattr(self, attr)) == 1:
                return getattr(self, attr)[0]
            raise ImproperInitializationError(
                instance=self,
                message=(
                    f"The exception class contains {len(self.detail)} details "
                    f"but only {len(getattr(self, attr))} {attr}(s).  If "
                    f"the details {attr}(s) are provided as arrays, their "
                    "lengths must be consistent."
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
        message_components = [utils.cjoin(
            self.indent, self.prefix, self.content)]
        if self.detail is not None:
            message_components += [
                utils.cjoin(
                    self.get_detail_attribute(i, 'detail_indent'),
                    self.get_detail_attribute(i, 'detail_prefix'),
                    d
                )
                for i, d in enumerate(self.detail)
            ]
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
            return utils.obj_name(self._func)
        return self._func

    @property
    def prefix(self):
        if self._func is not None:
            return (
                f"Improper Usage of Method {self.func_name} "
                f"on {self.cls_name}."
            )
        return f"Improper Usage of {self.cls_name}."

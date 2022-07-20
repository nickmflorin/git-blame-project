from .utils import klass


def validate_obj(instance, obj):
    if not isinstance(obj, (object, type)):
        raise ImproperInitializationError(instance, message=(
            "Expected a class or instance type but received "
            f"{type(obj)}."
        ))
    return obj


def validate_string(instance, value, param):
    if not isinstance(value, str):
        raise ImproperInitializationError(instance, message=(
            f"Expected a string type for `{param}` parameter, but "
            f"received {type(value)}."
        ))
    return value


def pluck_obj(instance, **kwargs):
    value = None
    if 'instance' in kwargs and kwargs['instance'] is not None:
        return validate_obj(instance, kwargs['instance'])
    elif 'cls' in kwargs and kwargs['cls'] is not None:
        return validate_obj(instance, kwargs['cls'])
    return value


def pluck_string(instance, param, **kwargs):
    value = None
    if param in kwargs and kwargs[param] is not None:
        return validate_string(instance, kwargs[param], param)
    return value


class ExceptionMetaClass(type):
    def __new__(cls, name, bases, dct):
        if name != 'AbstractException':
            # We do not allow the `message` attribute to be statically defined
            # on classes that extend the AbstractException base class.
            if 'message' in dct:
                raise TypeError(
                    f"The exception class {name} extends `AbstractException` "
                    "and cannot define the `message` attribute statically."
                )
        return super().__new__(cls, name, bases, dct)


class AbstractException(Exception, metaclass=ExceptionMetaClass):
    def __init__(self, *args, **kwargs):
        if len(args) not in (0, 1, 2):
            raise ImproperInitializationError(self, message=(
                "Expected 0, 1 or 2 positional arguments, but received "
                f"{len(args)}."
            ))
        self._obj = None
        self._message = None
        if len(args) == 2:
            if isinstance(args[0], str):
                self._message = args[0]
                self._obj = validate_obj(self, args[1])
            elif isinstance(args[1], str):
                self._message = args[1]
                self._obj = validate_obj(self, args[0])
            else:
                raise ImproperInitializationError(self, message=(
                    "Expected both a class or instance type and a message "
                    f"string, but received {type(args[0])} and {type(args[1])}."
                ))
        elif len(args) == 1:
            if isinstance(args[0], str):
                self._message = args[0]
                self._obj = pluck_obj(self, **kwargs)
            else:
                self._obj = validate_obj(self, args[0])
                self._message = pluck_string(self, 'message', **kwargs)
        else:
            self._obj = pluck_obj(self, **kwargs)
            self._message = pluck_string(self, 'message', **kwargs)

        self._detail = pluck_string(self, 'detail', **kwargs)
        self._detail_prefix = pluck_string(self, 'detail_prefix', **kwargs)
        self._message_prefix = pluck_string(self, 'message_prefix', **kwargs)

        if getattr(self, 'object_required', False) and self._obj is None:
            raise TypeError(
                "The object class or instance is required to initialize "
                f"{self.__class__}."
            )

    @property
    def cls(self):
        if self._obj is not None:
            return klass(self._obj)
        return None

    @property
    def cls_name(self):
        if self.cls is not None:
            return self.cls.__name__
        return None

    @classmethod
    def standardize_prefix(cls, prefix, content=None):
        end_characters = {
            True: ":",
            False: "."
        }
        prefix = prefix.strip()
        end_char = end_characters[content is not None]
        if not prefix.endswith(end_char):
            prefix = f"{prefix}{end_char}"
        return prefix

    @property
    def detail(self):
        return self._detail

    @property
    def detail_prefix(self):
        return self._detail_prefix or "Detail"

    @property
    def message_prefix(self):
        return self._message_prefix

    @property
    def content(self):
        return self._message

    def standardize_content_and_prefix(self, prefix=None, content=None,
            use_prefix_alone=True):
        mapping = {
            (True, True):
                f"{self.standardize_prefix(prefix, content=content)} {content}",
            (True, False):
                f"{self.standardize_prefix(prefix, content=content)}"
                if use_prefix_alone else None,
            (False, True): content,
            (False, False): None
        }
        return mapping[(prefix is not None, content is not None)]

    @property
    def message(self):
        base_message = self.standardize_content_and_prefix(
            prefix=self.message_prefix,
            content=self.content
        )
        if base_message is None:
            raise ImproperInitializationError(
                cls=self.__class__,
                message=(
                    f"The exception class {self.__class__} does not define a "
                    "message or a prefix."
                )
            )
        detail_message = self.standardize_content_and_prefix(
            prefix=self.detail_prefix,
            content=self.detail,
            use_prefix_alone=False
        )
        if detail_message is not None:
            return f"{base_message}\n{detail_message}"
        return base_message

    def __str__(self):
        return self.message


class ImproperInitializationError(AbstractException):
    object_required = True

    @property
    def message_prefix(self):
        return f"Improper Initialization of {self.cls.__name__}"


class GitBlameProjectError(AbstractException):
    pass

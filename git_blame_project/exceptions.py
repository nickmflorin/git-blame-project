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
    if 'instance' in kwargs:
        return validate_obj(instance, kwargs['instance'])
    elif 'cls' in kwargs:
        return validate_obj(instance, kwargs['cls'])
    return value


def pluck_string(instance, param, **kwargs):
    value = None
    if param in kwargs:
        return validate_string(instance, kwargs[param], param)
    return value


def pluck_message(instance, **kwargs):
    return pluck_string(instance, 'message', **kwargs)


def pluck_message_content(instance, **kwargs):
    return pluck_string(instance, 'message', **kwargs)


class AbstractException(Exception):
    def __init__(self, *args, **kwargs):
        if len(args) not in (0, 1, 2):
            raise ImproperInitializationError(self, message=(
                "Expected 0, 1 or 2 positional arguments, but received "
                f"{len(args)}."
            ))
        self._obj = None
        self._message = None
        self._message_content = kwargs.pop('message_content', None)
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
                self._message = pluck_message(self, **kwargs)
        else:
            self._obj = pluck_obj(self, **kwargs)
            self._message = pluck_message(self, **kwargs)

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
    def standardize_prefix(cls, prefix, has_message=True):
        end_characters = {
            True: ":",
            False: "."
        }
        prefix = prefix.strip()
        end_char = end_characters[has_message]
        if not prefix.endswith(end_char):
            prefix = f"{prefix}{end_char}"
        return prefix

    @property
    def message_content(self):
        return self._message_content

    @property
    def message(self):
        message = self._message or self.message_content
        prefix = None
        if getattr(self, 'message_prefix', None) is not None:
            prefix = self.standardize_prefix(
                prefix=self.message_prefix,
                has_message=message is not None
            )
        if message is None and prefix is None:
            raise TypeError(
                f"The exception class {self.__class__} was not initialized "
                "with a message nor does it define one statically."
            )
        if prefix is not None and message is not None:
            return f"{prefix} {message}"
        elif prefix is not None:
            return prefix
        return message

    def __str__(self):
        return self.message


class ImproperInitializationError(AbstractException):
    object_required = True

    @property
    def message_prefix(self):
        return f"Improper Initialization of {self.cls.__name__}"


class GitBlameProjectError(AbstractException):
    pass

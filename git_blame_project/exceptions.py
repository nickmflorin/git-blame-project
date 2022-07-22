from .utils import obj_name, humanize_list, ensure_iterable, is_iterable


def validate_obj_name(obj, param, value):
    if not isinstance(value, (object, type)):
        raise ImproperInitializationError(obj, message=(
            f"Expected a class or instance type for param `{param}` but "
            f"received {type(value)}."
        ))
    return obj_name(value)


def validate_string(obj, param, value):
    if value is not None and not isinstance(value, str):
        raise ImproperInitializationError(obj, message=(
            f"Expected a string type for `{param}` parameter, but "
            f"received {type(value)}."
        ))
    return value


def validate_details(obj, param, value):
    if not isinstance(value, (str, list, tuple)):
        raise ImproperInitializationError(obj, message=(
            f"Expected a string, list or tuple type for `{param}` "
            f"parameter, but received {type(value)}."
        ))
    elif isinstance(value, (list, tuple)):
        non_string_details = [d for d in value if not isinstance(d, str)]
        if non_string_details:
            non_string_types = set([type(d) for d in non_string_details])
            humanized = humanize_list(non_string_types)
            raise ImproperInitializationError(obj, message=(
                f"Expected all elements of the iterable for the `{param}` "
                f"param to be a string, but received {humanized}."
            ))
    return value


def plucker(validator, param=None):
    def pluck(obj, **kwargs):
        if param is None and 'param' not in kwargs:
            raise TypeError("The parameter name must be provided.")
        params = ensure_iterable(param)
        for p in params:
            if p in kwargs and kwargs[p]:
                if kwargs[p] is not None:
                    return validator(obj, p, value=kwargs[p])
                return None
        return None
    return pluck


pluck_obj_name = plucker(validate_obj_name, param=['instance', 'cls'])
pluck_string = plucker(validate_string)
pluck_detail = plucker(validate_details, param='detail')
pluck_detail_prefix = plucker(validate_details, param='detail_prefix')


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
    detail_indent = True

    def __init__(self, *args, **kwargs):
        if len(args) not in (0, 1, 2):
            raise ImproperInitializationError(self, message=(
                "Expected 0, 1 or 2 positional arguments, but received "
                f"{len(args)}."
            ))
        if len(args) == 2:
            if isinstance(args[0], str):
                self._message = args[0]
                self._cls_name = validate_obj_name(
                    self, param='obj', value=args[1])
            elif isinstance(args[1], str):
                self._message = args[1]
                self._cls_name = validate_obj_name(
                    self, param='obj', value=args[0])
            else:
                raise ImproperInitializationError(self, message=(
                    "Expected both a class or instance type and a message "
                    f"string, but received {type(args[0])} and {type(args[1])}."
                ))
        elif len(args) == 1:
            if isinstance(args[0], str):
                self._message = args[0]
                self._cls_name = pluck_obj_name(self, **kwargs)
            else:
                self._cls_name = validate_obj_name(self, 'obj', value=args[0])
                self._message = pluck_string(self, param='message', **kwargs)
        else:
            self._cls_name = pluck_obj_name(self, **kwargs)
            self._message = pluck_string(self, param='message', **kwargs)

        self._detail = pluck_detail(self, **kwargs)
        self._detail_prefix = pluck_detail_prefix(self, **kwargs)
        self._prefix = pluck_string(self, param='prefix', **kwargs)

        if getattr(self, 'object_required', False) and self._cls_name is None:
            raise TypeError(
                "The object class or instance is required to initialize "
                f"{self.__class__}."
            )

    @property
    def cls_name(self):
        return self._cls_name

    @property
    def detail(self):
        return self._detail

    @property
    def detail_prefix(self):
        return self._detail_prefix or "Detail"

    @property
    def prefix(self):
        return self._prefix

    @property
    def content(self):
        return self._message

    @classmethod
    def standardize_prefix(cls, prefix=None, end_char=':', is_detail=False):
        if end_char not in (':', '.'):
            raise ValueError(
                f"Invalid end character {end_char}.  Must be `:` or `.`.")
        if prefix is not None:
            prefix = prefix.strip()
            if not prefix.endswith(end_char):
                prefix = f"{prefix}{end_char}"
            if is_detail:
                if cls.detail_indent is True \
                        or isinstance(cls.detail_indent, str):
                    detail_indent = "-->" if cls.detail_indent is True \
                        else cls.detail_indent
                    return f"{detail_indent} {prefix}"
        return prefix

    @classmethod
    def content_and_prefix(cls, prefix=None, content=None, is_detail=False):
        prefix = cls.standardize_prefix(
            prefix=prefix,
            end_char="." if content is None else ":",
            is_detail=is_detail
        )
        mapping = {
            (True, True): f"{prefix} {content}",
            (True, False): prefix if not is_detail else None,
            (False, True): content,
            (False, False): None
        }
        return mapping[(prefix is not None, content is not None)]

    @property
    def message(self):
        # It is important to revalidate any values just in case they were
        # provided as overridden methods.
        prefix = validate_string(self, 'prefix', value=self.prefix)
        content = validate_string(self, 'content', value=self.content)
        if prefix is None and content is None:
            raise ImproperInitializationError(
                instance=self,
                message=(
                    f"The exception class {self.__class__} does not define a "
                    "message or a prefix."
                )
            )
        message_components = [self.content_and_prefix(
            prefix=prefix,
            content=content
        )]
        detail = validate_details(self, 'detail', self.detail)
        if detail is not None:
            detail = ensure_iterable(detail)
            for i, d in enumerate(detail):
                detail_prefix = self.detail_prefix
                if is_iterable(detail_prefix):
                    try:
                        detail_prefix = detail_prefix[i]
                    except IndexError as e:
                        raise ImproperInitializationError(
                            instance=self,
                            message=(
                                f"The exception class contains {len(detail)} "
                                f"details but only {len(detail_prefix)} "
                                "prefixes.  They must be consistent."
                            )
                        ) from e
                component = self.content_and_prefix(
                    prefix=detail_prefix,
                    content=d,
                    is_detail=True
                )
                if component is not None:
                    message_components.append(component)
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

import functools

from git_blame_project import utils

from .meta import ExceptionMetaClass
from .models import StringFormatChoices, Formatter, ExceptionAttribute


class AbstractException(Exception, metaclass=ExceptionMetaClass):
    """
    Abstract base class for all :obj:`Exception` classes used in this project.
    This :obj:`Exception` class should never be used alone, but only via an
    :obj:`Exception` class that extends it.

    Parameters:
    ----------
    For all attributes of the :obj:`AbstractException` class and its
    extensions, each attribute can be established in the following ways:

    (1) Statically on the :obj:`AbstractException` class as a simple property.
    (2) Statically on the :obj:`AbstractException` class as an @property.
    (3) Dynamically on initialization of the :obj:`AbstractException` class.

    In all cases, the :obj:`ExceptionMetaClass` will be used to wrap the
    attribute in an @property to ensure it is retrieved from the correct
    source (initialization arguments or static class attributes) and
    formatted when accessed.

    Additionally, all parameters of exceptions that extend the this base
    :obj:`AbstractException` class can have a default value defined statically
    on the class, `default_<attribute_name>` - which will only be used in the
    case that it is not provided via initialization and not defined statically
    on the class.

    >>> class MyCustomException(AbstractException):
    >>>     default_klass = 'MyCustomObj'
    >>>
    >>> exc = MyCustomException(klass=MySecondCustomObj)
    >>> exc.klass = 'MySecondCustomObj'
    >>>
    >>> exc = MyCustomException()
    >>> exc.klass = 'MyCustomObj'

    content: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that refer
        to the core message the exception will display in the string form of the
        exception on the first line.

        The :obj:`str` instance, or each :obj:`str` instance in the iterable,
        can contain string formatted arguments that are properties on the
        :obj:`AbstractException` instance they are associated with.  These
        string formatted arguments will be automatically included in the message
        when the :obj:`AbstractException` renders if they are present on the
        :obj:`AbstractException` instance and non-null.

        If the `content` parameter is an iterable of :obj:`str` instances, the
        :obj:`str` instance in the iterable will be chosen such that the number
        of non-null string formatted arguments associated with the :obj:`str`
        instance is optimized.

        Example:
        -------
        Consider the following `content` definition:

        >>> content = [
        >>>     "The {animal} jumped over the {object}.",
        >>>     "The {animal} jumped over something.",
        >>>     "Some animal jumped over something."
        >>> ]

        Assume that we have an exception instance `e = MyException()` that
        defines the `content` attribute as shown above, if `e.animal` is not
        None but `e.object` is None, the second formatted string in the
        `content` array will be used.

        Default: None

    prefix: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that will
        be displayed in front of the main exception `content` in the string
        form of the exception instance.

        The :obj:`str` instance can contain string formatted arguments that
        are properties on the :obj:`AbstractException` instance they are
        used to initialize.

        If the `prefix` parameter is an iterable of :obj:`str` instances, the
        :obj:`str` instance in the iterable will be chosen such that the number
        of non-null string formatted arguments associated with the :obj:`str`
        instance is optimized.

        Default: None

    indent: :obj:`str` (optional)
        A :obj:`str` that will be displayed in front of the combined message
        `content` and `prefix`.  This will typically be an empty string.

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

        Default: None

    detail_prefix: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that define
        the prefixes that will be shown before each detail in the string form
        of the exception.

        If it is desired that the same prefix be used for all details, it can
        be provided as a simple string.  Otherwise, it can be provided as an
        array to indicate the specific prefixes to use for each detail line.

        Default: None

    detail_indent: :obj:`str` or :obj:`tuple` or :obj:`list` (optional)
        Either a :obj:`str` or an iterable of :obj:`str` instances that define
        the indents that will be displayed before each combined detail prefix
        and detail line.

        If it is desired that the same indent be used for all details, it can
        be provided as a simple string.  Otherwise, it can be provided as an
        array to indicate the specific indents to use for each detail line.

        Default: "--> "
    """
    attributes = [
        ExceptionAttribute(name='detail', formatter=utils.ensure_iterable),
        ExceptionAttribute(
            name='detail_indent',
            formatter=utils.ensure_iterable
        ),
        ExceptionAttribute(name='indent'),
        ExceptionAttribute(
            name='content',
            accessor='message',
            formatter=Formatter(lambda instance: [
                utils.ensure_iterable,
                StringFormatChoices.flattener(instance),
                functools.partial(
                    utils.conditionally_format_string,
                    obj=instance
                )
            ])
        ),
        ExceptionAttribute(
            name='detail_prefix',
            formatter=Formatter(lambda instance: [
                utils.ensure_iterable,
                StringFormatChoices.flattener(instance),
                functools.partial(
                    utils.conditionally_format_string,
                    obj=instance,
                    # We want each detail prefix to be formatted and returned.
                    optimized=False,
                )
            ])
        ),
        ExceptionAttribute(
            name='prefix',
            formatter=Formatter(lambda instance: [
                utils.ensure_iterable,
                StringFormatChoices.flattener(instance),
                functools.partial(
                    utils.conditionally_format_string,
                    obj=instance,
                )
            ])
        ),
    ]
    default_detail_indent = "--> "

    def __init__(self, **kwargs):
        for attr in self.attributes:
            required_attrs_on_init = getattr(self, 'required_on_init', [])
            if attr.accessor in required_attrs_on_init \
                    and kwargs.get(attr.accessor, None) is None:
                raise TypeError(
                    f"The parameter {attr.accessor} is required to initialize "
                    f"the exception class {self.__class__}."
                )
            setattr(self, f'_{attr.name}', kwargs.pop(attr.accessor, None))

    def get_detail_attribute(self, i, attr):
        if getattr(self, attr) is None:
            return None
        try:
            return getattr(self, attr)[i]
        except IndexError:
            # If there is only one attribute in the array, it means that it was
            # most likely provided as a single value and it should be used for
            # all details in the array.
            if len(getattr(self, attr)) == 1:
                return getattr(self, attr)[0]
            # If there is more than one attribute in the array, but the index
            # doesn't exist (i.e. the array is too short) - just return the last
            # element of the array.
            return getattr(self, attr)[-1]

    @classmethod
    def opposite_end_char(cls, end_char):
        return {
            '.': ':',
            ':': '.'
        }[end_char]

    @classmethod
    def format_prefix_value(cls, value, msg):
        end_char = '.' if msg is None else ':'
        if value is not None:
            if not value.endswith(end_char):
                if value.endswith(cls.opposite_end_char(end_char)):
                    value = value[:-1]
                return f"{value}{end_char}"
        return value

    @property
    def message(self):
        message_components = [utils.cjoin(
            self.indent,
            self.format_prefix_value(self.prefix, self.content),
            self.content
        )]
        if self.detail is not None:
            message_components += [
                utils.cjoin(
                    self.get_detail_attribute(i, 'detail_indent'),
                    self.format_prefix_value(
                        self.get_detail_attribute(i, 'detail_prefix'),
                        d
                    ),
                    utils.conditionally_format_string(d, self)
                )
                for i, d in enumerate(self.detail)
            ]
        return "\n".join(message_components)

    def __str__(self):
        return self.message

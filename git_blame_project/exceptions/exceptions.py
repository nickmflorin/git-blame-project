from git_blame_project import utils

from .base import AbstractException
from .models import StringFormatChoices, ExceptionAttribute


class GitBlameProjectError(AbstractException):
    """
    Base class for all exceptions that may surface to the user, typically
    in a formatted form.
    """


class ImproperUsageError(GitBlameProjectError):
    """
    A general exception that is raised when a function is improperly used
    or a class is improperly initialized.

    This can include, but is not limited to, situations such as missing
    parameters or invalid parameters - each of which have more specific
    exception classes that extend this more general :obj:`ImproperUsageError`
    exception class.  However, it is not necessary to subclass this exception
    class, and it can be used in its more general form for a wide range of
    circumstances.

    This exception class, and extensions of this extension class, can
    optionally include context about the class or the function that is being
    improperly used.

    Parameters:
    -----------
    Like all attributes of the :obj:`AbstractException` class and its
    extensions, each attribute can be provided on initialization, defined
    statically on the class as a simple attribute or defined statically
    on the class as an @property.

    In all cases, the :obj:`ExceptionMetaClass` will be used to wrap the
    attribute in an @property to ensure it is retrieved from the correct
    source (initialization arguments or static class attributes) and
    formatted when accessed.

    klass: :obj:`str`, :obj:`type` or :obj:`object` (optional)
        The class or instance that the improper usage is related to - if
        applicable.  Can be provided as a string name of the class, the
        class itself or an instance of the class.

        Default: None

    func: :obj:`str` or :obj:`lambda` (optional)
        The function name or function itself that the improper usage is
        related to - if applicable.

        Default: None
    """
    attributes = [
        ExceptionAttribute(name='klass', formatter=utils.obj_name),
        ExceptionAttribute(name='func', formatter=utils.obj_name)
    ]
    prefix = [
        StringFormatChoices(
            func=lambda instance: instance.klass is not None
            or instance.func is not None,
            isolated=True,
            choices=[
                "Improper usage of method {func} on class {klass}.",
                "Improper initialization of class {klass}.",
                "Improper usage of method {func}.",
            ]
        )
    ]


class ParamError(ImproperUsageError):
    """
    A general exception that is raised when there is an error related to a
    parameter or several parameters that are provided to a function or class.

    Parameters:
    ----------
    Like all attributes of the :obj:`AbstractException` class and its
    extensions, each attribute can be provided on initialization, defined
    statically on the class as a simple attribute or defined statically
    on the class as an @property.

    In all cases, the :obj:`ExceptionMetaClass` will be used to wrap the
    attribute in an @property to ensure it is retrieved from the correct
    source (initialization arguments or static class attributes) and
    formatted when accessed.

    param: :obj:`str`, :obj:`tuple` or :obj`list` (optional)
        The single parameter or several parameters that the error is related to.

        Default: None

    conjunction: :obj:`str` (optional)
        Either "or" or "and", which is used to humanize the array of parameters
        into a human readable string.

        Default: "and"
    """
    attributes = [
        ExceptionAttribute(
            name='param',
            formatter=utils.ensure_iterable,
            # If the value is None, we want an empty list to be returned.
            format_null_values=True
        ),
        ExceptionAttribute(name='conjunction', default="and"),
    ]

    @property
    def humanized_param(self):
        if len(self.param) == 0:
            return None
        elif len(self.param) == 1:
            return self.param[0]
        return utils.humanize_list(self.param, conjunction=self.conjunction)


class RequiredParamError(ParamError):
    """
    An exception that is raised when one or more parameters are required
    for a function call or class instantiation but are not provided.
    """
    content = [
        StringFormatChoices(
            func=lambda instance: len(instance.param) == 1,
            isolated=True,
            choices=[
                "The parameter `{humanized_param}` is required.",
                "The parameter is required.",
            ]
        ),
        StringFormatChoices(
            func=lambda instance: len(instance.param) != 1
                and instance.conjunction == 'or',
            isolated=True,
            choices=[
                "One of the parameters {humanized_param} is required.",
                "One of the parameters is required.",
            ]
        ),
        StringFormatChoices(
            func=lambda instance: len(instance.param) != 1
                and instance.conjunction != 'or',
            isolated=True,
            choices=[
                "All of the parameters {humanized_param} are required.",
                "All of the parameters are required.",
            ]
        )
    ]


class InvalidParamError(ParamError):
    """
    An exception that is raised when one or more parameters are provided to
    a function call or class instantiation but are invalid.

    Parameters:
    ----------
    Like all attributes of the :obj:`AbstractException` class and its
    extensions, each attribute can be provided on initialization, defined
    statically on the class as a simple attribute or defined statically
    on the class as an @property.

    In all cases, the :obj:`ExceptionMetaClass` will be used to wrap the
    attribute in an @property to ensure it is retrieved from the correct
    source (initialization arguments or static class attributes) and
    formatted when accessed.

    value: (optional)
        A single value or multiple values that were invalid and associated with
        the parameters that were provided to this exception class.

        Default: None

    valid_types: :obj:`type` or :obj:`tuple` or :obj:`list` (optional)
        Either a single type or several types of which the parameter was
        expected to be of.

        Default: None
    """
    attributes = [
        ExceptionAttribute(
            name='value',
            formatter=utils.ensure_iterable,
            # If the value is not provided, we want it to be treated as an
            # empty array - not null.
            format_null_values=True,
        ),
        ExceptionAttribute(name='value_formatter'),
        ExceptionAttribute(
            name='valid_types',
            formatter=utils.ensure_iterable,
            # If the valid_types are not provided, we want it to be treated as
            # an empty array - not null.
            format_null_values=True,

        ),
    ]
    content = [
        StringFormatChoices(
            func=lambda instance: len(instance.value) > 1,
            isolated=True,
            choices=[
                "Received invalid values for parameter or parameters.",
                "Received invalid values {humanized_value}.",
                "Received invalid values {humanized_value} for "
                "param(s) {humanized_param}.",
                "Received invalid values {humanized_value} for "
                "param(s) {humanized_param}, "
                "expected values of type {humanized_valid_types}.",
                "Received invalid values {humanized_value}, "
                "expected values of type {humanized_valid_types}.",
            ]
        ),
        StringFormatChoices(
            func=lambda instance: len(instance.value) == 1,
            isolated=True,
            choices=[
                "Received invalid value for parameter.",
                "Received invalid value {humanized_value}.",
                "Received invalid value {humanized_value} for "
                "param(s) {humanized_param}.",
                "Received invalid value {humanized_value} for "
                "param(s) {humanized_param}, "
                "expected values of type {humanized_valid_types}.",
                "Received invalid value {humanized_value}, "
                "expected values of type {humanized_valid_types}.",
            ]
        ),
        StringFormatChoices(
            func=lambda instance: len(instance.value) == 0,
            isolated=True,
            choices=[
                "Received invalid value for param(s).",
                "Received invalid value for param(s) {humanized_param}.",
                "Received invalid value for param(s) {humanized_param}, "
                "expected {humanized_valid_types}.",
                "Received invalid value, expected {humanized_valid_types}.",
            ]
        )

    ]

    @property
    def humanized_value(self):
        if len(self.value) == 0:
            return None
        elif len(self.value) == 1:
            return self.format(self.value[0])
        return utils.humanize_list(
            set([self.format(v) for v in self.value]),
            conjunction='and'
        )

    @property
    def humanized_valid_types(self):
        if len(self.valid_types) == 0:
            return None
        return utils.humanize_list(self.valid_types, conjunction="or")

from .builtins import empty, ensure_iterable, get_attribute, is_iterable
from .formatters import humanize_list


class ConditionalString:
    def __init__(self, string, conditional, alternate=None):
        self._string = string
        self._conditional = conditional
        self._alternate = alternate

    def value(self):
        if self._conditional:
            return self._alternate
        return self._string


def cjoin(*args, delimiter=" ", invalids=empty, formatter=None):
    """
    Conditionally joins a series of arguments that are validated before being
    combined into a single string where each string part is separated by the
    `delimeter` parameter.

    Parameters:
    ----------
    *args
        A series of objects that should be combined into the single string
        if they pass validation.  If the argument is an instance of
        :obj:`ConditionalString`, it will only be included if the conditional
        attached to the object evaluates to True.

    delimiter: :obj:`str` (optional)
        The string separator that should separate the individual string
        arguments that pass validation into a single string.

        Default: " "

    invalids: :obj:`list` or :obj:`tuple` or any value (optional)
        Either an iterable of values or a single value that dictate what
        values are excluded from the conditionally joined string.

        If not provided, the default value is `None` - which means that `None`
        values will be excluded from the joined string.

        Default: None

    formatter: :obj:`lambda` (optional)
        A formatting function that if provided, will be applied to the
        individual string arguments that pass validation before they are
        joined into a single string.

        Default: None
    """
    string_args = []
    invalids = ensure_iterable(empty.default(invalids, [None]))
    for a in args:
        if a not in invalids:
            if formatter is not None:
                string_args.append(formatter(str(a)))
            else:
                string_args.append(str(a))
    if len(string_args) == 0:
        return ""
    return delimiter.join(string_args)


cjoin.Conditional = ConditionalString


def get_string_formatted_kwargs(value):
    """
    Returns the string arguments that are used to format the string.

    Example:
    --------
    In the string foo = "Hello {world}", the string foo would be formatted as
    foo.format(world='bar').  In this case, this method will return ["world"],
    indicating that `world` is the only argument needed to format the string.
    """
    formatted_kwargs = []
    current_formatted_kwarg = None
    for char in value:
        if char == "{":
            current_formatted_kwarg = ""
        elif char == "}":
            if current_formatted_kwarg is not None:
                if current_formatted_kwarg not in formatted_kwargs:
                    formatted_kwargs.append(current_formatted_kwarg)
                current_formatted_kwarg = None
        else:
            if current_formatted_kwarg is not None:
                current_formatted_kwarg = current_formatted_kwarg + char
    return formatted_kwargs


def conditionally_format_string(string, *args, **kwargs):
    """
    Conditionally formats a string or several strings based on what parameters
    are present in an associated class, instance, dictionary or set of keyword
    parameters.

    Background:
    ----------
    Traditionally, when you have a string with format arguments in it,
    formatting the string via the format() method will raise an error if:

    (1) Not all of the arguments are provided.
    (2) Additional arguments are provided.

    Here, we loosen that constraint such that the string will only have
    values injected into locations where there is a format argument
    (i.e. "{injected_value_here}") if that argument is present and non-null.

    Behavior:
    --------
    This method behaves in (3) distinct ways:

    (1) Formatting the Optimal String
        This behavior occurs when multiple strings are provided and the
        `optimized` parameter is either not provided or `False`.

        When this is the case, the optimal string is chosen based on the choice
        with the most injectable format arguments and the fewest missing format
        arguments:

        >>> conditionally_format_string([
        >>>     "The {animal} jumped over the {object}.",
        >>>     "The {animal} jumped over something.",
        >>>     "Some animal jumped over something."
        >>> ], {"animal": "dog"})
        >>> "The dog jumped over something."

    (2) Formatting the Only String
        This behavior occurs when only one string is provided, regardless of
        the value of the `optimized` parameter.

        When this is the case, the single string is formatted based on the
        provided class, instance, dictionary or set of keyword arguments:

        >>> conditionally_format_string(
        >>>     "The {animal} jumped over the {object}.",
        >>>     animal="dog"
        >>> )
        >>> "The dog jumped over the {object}."

    (3) Formatting Multiple Strings
        This behavior occurs when multiple strings are provided and the
        `optimized` parameter is provided and is `False`.

        When this is the case, each string is formatted separately and returned
        as an array.

        >>> conditionally_format_string([
        >>>     "The {animal} jumped over the {object}.",
        >>>     "The {animal} jumped over something.",
        >>>     "Some animal jumped over something."
        >>> ], {"animal": "dog"}, optimized=False)
        >>> [
        >>>     "The dog jumped over the {object}.",
        >>>     "The dog jumped over something.",
        >>>     "Some animal jumped over something."
        >>> ]

    Injecting:
    ---------
    The values that are injected into the provided string(s) can be obtained
    from a variety of sources.

    (1) A Class
        Here, a class can be provided to the method and injectable arguments
        will be looked for in the static attributes of the class

        >>> my_string = "Welcome to {name}, written by {author}."
        >>> my_class = MyObject
        >>> my_class.name = 'App'
        >>> conditionally_format_string(my_string, my_class)
        >>> >>> "Welcome to App, written by {author}."

    (2) A Class Instance
        Here, a class can be provided to the method and injectable arguments
        will be looked for in the attributes of the class instance.

        >>> my_string = "Welcome to {name}, written by {author}."
        >>> my_object = MyObject(name='App', author='John')
        >>> conditionally_format_string(my_string, my_object)
        >>> >>> "Welcome to App, written by John."

    (3) A Dictionary
        Here, a :obj:`dict` can be provided to the method and the injectable
        arguments will be looked for in the keys of the :obj:`dict`.

        >>> my_string = "Welcome to {name}, written by {author}."
        >>> conditionally_format_string(my_string, {'author': 'John'})
        >>> "Welcome to {name}, written by John."

    (4) **kwargs
        Here, the injectable arguments will be looked for in the keys of the
        keyword arguments.

        >>> my_string = "Welcome to {name}, written by {author}."
        >>> conditionally_format_string(my_string, author="John", name="App")
        >>> "Welcome to App, written by John."

    Parameters:
    ----------
    string: :obj:`str` or :obj:`list` or :obj:`tuple`
        Either a :obj:`str` instance or an iterable of :obj:`str` that should
        be formatted.

        If provided as an iterable, the best choice string will be chosen in the
        case that `optimized` is True, otherwise all strings in the array will
        be formatted and returned.

    obj: :obj:`dict` or :obj:`object` or :obj:`type`
        The object that contains the values for the formatting arguments in the
        string.  If provided as a :obj:`dict`, the values will be retrieved
        via key lookup.  If provided as an :obj:`object` or :obj:`type`, the
        value will be retrieved via attribute lookup.

        This parameter can either be provided as the second argument to the
        method, a keyword argument `obj` or as keyword arguments.

    optimized: :obj:`bool` (optional)
        Whether or not the best choice string should be chosen, formatted and
        returned in the case that the `string` parameter is provided as an
        iterable.  If `optimized` is False, all strings in the iterable will
        be formatted and an iterable of formatted strings will be returned.

        Default: True

    is_null: :obj:`lambda` (optional)
        A callback function that indicates whether or not a given value should
        be treated as null and not injected into the formatted string.  This
        is typically used if there are cases where we want to avoid injecting
        empty iterables or other null-ish values into the string.

        Default: lambda v: v is None
    """
    from git_blame_project import exceptions

    if len(args) not in (0, 1):
        raise TypeError(f"Expected 0 or 1 arguments but received {len(args)}.")

    optimized = kwargs.pop('optimized', True)
    is_null = kwargs.pop('is_null', lambda v: v is None)

    obj = None
    if args:
        obj = args[0]
        humanized = humanize_list((dict, object, type), conjunction='or')
        if not isinstance(obj, (dict, object, type)):
            raise TypeError(
                f"Expected value to be of type {humanized}, received "
                f"{type(obj)}."
            )
    elif 'obj' in kwargs:
        obj = kwargs.pop('obj')
    else:
        obj = dict(kwargs)

    def count_params_present(params, obj):
        """
        Counts the number of formatted parameters in a string that exist on the
        provided object or set of keyword arguments.
        """
        return len([
            v for v in
            [get_attribute(obj, p, strict=False) for p in params]
            if not is_null(v)
        ])

    def get_best_string_choice(string_choices, obj):
        """
        Determines the best choice from a set of strings with format arguments
        such that the chosen string has the highest number of format arguments
        present on the provided object or set of keyword arguments.

        The best choice is determined by minimizing the number of missing
        format argument values while maximizing the number of format arguments
        possible.
        """
        # The string_choices will not be None or an empty iterable since the
        # calling logic will not call this method if that is the case.
        string_choices = ensure_iterable(string_choices)
        if len(string_choices) == 0:
            return None

        counts = []
        for string_choice in string_choices:
            format_args = get_string_formatted_kwargs(string_choice)
            present_args = count_params_present(format_args, obj)
            counts.append((
                string_choice,
                len(format_args),
                present_args,
                len(format_args) - present_args
            ))
        # Determine the string choices that have the minimum number of missing
        # format arguments.
        minimum_missing = min(t[3] for t in counts)
        choices_with_min_missing = [c for c in counts if c[3] == minimum_missing]
        # From those choices, determine the choice that has the maximum number of
        # format args in the original string.
        maximum_present = max(t[1] for t in choices_with_min_missing)
        return [
            c[0] for c in choices_with_min_missing
            if c[1] == maximum_present
        ][0]

    def conditionally_format(s):
        string_formatted_args = get_string_formatted_kwargs(s)
        for injectable_name in string_formatted_args:
            value = get_attribute(obj, injectable_name, strict=False)
            if not is_null(value):
                s = s.replace("{%s}" % injectable_name, str(value))
        return s.strip()

    if string is None or (is_iterable(string) and len(string) == 0):
        return None
    # If optimized is True, return a singular string from the potentially
    # multiple string options - where that singular string is optimized for
    # the number of formatting arguments that are able to be injected.
    elif optimized:
        strings = ensure_iterable(string)
        if any([not isinstance(x, str) for x in strings]):
            raise exceptions.InvalidParamError(
                param='string',
                valid_types=(str, ),
                message=(
                    "Expected all values in the {humanized_param} array "
                    "to be of type {humanized_valid_types}."
                )
            )
        best_choice_string = get_best_string_choice(strings, obj)
        return conditionally_format(best_choice_string)
    # If optimized is not True, return a singular formatted string in the case
    # that only 1 string was provided and return an array of formatted strings
    # in the case that multiple strings were provided.
    elif is_iterable(string):
        if any([not isinstance(x, str) for x in string]):
            raise exceptions.InvalidParamError(
                param='string',
                valid_types=(str, ),
                message=(
                    "Expected all values in the {humanized_param} array "
                    "to be of type {humanized_valid_types}."
                )
            )
        return [conditionally_format(s) for s in string]
    return conditionally_format(string)

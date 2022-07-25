import importlib

from .formatters import humanize_list


class empty:
    """
    This class is used to represent no data being provided for a given input
    or output value.
    It is required because `None` may be a valid input or output value.
    """
    @classmethod
    def default(cls, value, default):
        if value is empty:
            return default
        return value

    @classmethod
    def choose_first_non_empty(cls, *args, default):
        for a in args:
            if a is not cls:
                return a
        return default


class LazyFn:
    def __init__(self, func, *args, **kwargs):
        self._func = func
        if len(args) == 0 and 'args' in kwargs:
            self._args = list(kwargs.pop('args'))
        else:
            self._args = list(args)
        if 'kwargs' in kwargs:
            self._kwargs = kwargs.pop('kwargs')
        else:
            self._kwargs = kwargs

    def __call__(self):
        arguments = []
        for argument in self._args:
            if is_function(argument):
                arguments.append(argument())
            else:
                arguments.append(argument)
        return self._func(*arguments, **self._kwargs)


def klass(instance_or_cls):
    if not isinstance(instance_or_cls, type):
        return instance_or_cls.__class__
    return instance_or_cls


def obj_name(obj):
    if isinstance(obj, str):
        return obj
    elif hasattr(obj, '__name__'):
        return obj.__name__
    elif hasattr(obj, '__class__'):
        return obj.__class__.__name__
    else:
        raise TypeError(
            f"Expected the `obj` parameter to be of type {str}, {object} or "
            f"{type}, not {type(obj)}"
        )


def is_function(func):
    return hasattr(func, '__call__') and type(func) is not type


def is_iterable(value):
    return not isinstance(value, str) and hasattr(value, '__iter__')


def iterable_from_args(*args, cast=list, strict=True):
    if len(args) == 0:
        if strict:
            raise ValueError("At least one value must be provided.")
        return []
    elif len(args) == 1:
        if hasattr(args[0], '__iter__') and not isinstance(args[0], str):
            return cast(args[0])
        return cast([args[0]])
    else:
        return cast(args[:])


def ensure_iterable(value, strict=False, cast=list, cast_none=True):
    """
    Ensures that the provided value is an iterable that can be indexed
    numerically.
    """
    if value is None:
        if cast_none:
            return cast()
        return None
    # A str instance has an `__iter__` method.
    if isinstance(value, str):
        return [value]
    elif hasattr(value, '__iter__') and not isinstance(value, type):
        # We have to cast the value instead of just returning it because a
        # instance of set() has the `__iter__` method but is not indexable.
        return cast(value)
    elif strict:
        raise ValueError("Value %s is not an iterable." % value)
    return cast([value])


def import_at_module_path(module_path):
    """
    Imports the class or function at the provided module path.
    """
    module_name = ".".join(module_path.split(".")[:-1])
    class_name = module_path.split(".")[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def get_attribute(*args, **kwargs):
    """
    Reads the provided attribute from the object which can be a :obj:`dict`
    instance, a class or a class instance.

    Parameters:
    ----------
    obj: :obj:`type` or :obj:`object` or :obj:`dict` (optional)
        The object for which the attribute is read from.  If not provided
        as a positional argument, the mapping of keyword arguments will be used.

    attr: :obj:`str`
        The string name of the attribute on the provided `obj`.  The atttribute
        can be nested, where each nested attribute is separated by the
        `delimiter`.  In other words, if the attribute is `foo.bar` the
        returned value will be the value of the `bar` attribute on or in the
        value of the `foo` attribute on or in the original object.

    strict: :obj:`bool` (optional)
        Whether or not an exception should be raised if the provided `attr`
        does not exist on the provided `obj` (in the case that it is a
        :obj:`type` or :obj:`object`) or does not exist in the provided `obj`
        (in the case it is a :obj:`dict`).

        Default: True

    default (optional)
        The default value that should be used in the case that `strict` is
        `False` and the attribute does not exist in or on the provided `obj`.

        Default: None

    delimiter: :obj:`str` (optional)
        In the case that the attribute is
        Default: None
    """
    options = {
        'strict': kwargs.pop('strict', True),
        'default': kwargs.pop('default', None),
        'delimiter': kwargs.pop('delimiter', '.')
    }

    if len(args) not in (1, 2):
        raise TypeError(
            "The number of positional arguments should be 1 or 2, but "
            f"received {len(args)}."
        )
    elif len(args) == 2:
        obj = args[0]
        attr = args[1]
    else:
        obj = dict(kwargs)
        attr = args[0]

    if not isinstance(obj, (dict, object, type)):
        raise TypeError(
            f"Expected the `obj` parameter to be of type {dict}, {object} or "
            f"{type}, but received {type(obj)}."
        )

    if options['delimiter'] in attr:
        parts = attr.split(options['delimiter'])
        # If the attribute is nested but is still one attribute (i.e. `foo.`),
        # just call the original function with the "." removed.
        if len(parts) == 1:
            return get_attribute(obj, parts[0], **options)
        # If the attribute is nested, the higher level objects returned by
        # the nested attributes up until the last separated attribute cannot
        # use a default and must be strict.
        value = get_attribute(
            obj, parts[0], strict=True, delimiter=options['delimiter'])
        return get_attribute(
            value, options['delimiter'].join(parts[1:]), **options)

    if isinstance(obj, dict):
        if attr not in obj and options['strict']:
            raise KeyError(
                f"The attribute {attr} does not exist in the provided "
                "dictionary."
            )
        return obj.get(attr, options['default'])
    elif not hasattr(obj, attr) and options['strict']:
        raise AttributeError(
            f"The attribute {attr} does not exist on the provided "
            f"{obj_name(obj)}."
        )
    return getattr(obj, attr, options['default'])


def parse_duplicates(array, attr=None, starting_array=None, prioritized=None):
    """
    Removes the duplicates in the provided `array` and returns the array with
    duplicates removed and the duplicate values that were found.

    Parameters:
    ----------
    array: :obj:`list` or :obj:`tuple`
        The primary iterable for which the duplicates are being removed.

    attr: :obj:`string` (optional)
        The attribute of the elements in each array that uniquely identifies
        one element from another.

        Default: None

    starting_array: :obj:`list` or :obj:`tuple` (optional)
        The iterable that the non-duplicate values of the primary `array`
        should be added to.  Only applicable when merging arrays.

        Default: None

    prioritized: :obj:`lambda` (optional)
        A function callback that takes a given value in the array as its first
        and only argument and returns a boolean indicating whether or not the
        value should be prioritized over others.

        In the case that the callback indicates that the value should be
        prioritized over others, it will replace
    """
    from git_blame_project import exceptions

    flattened_array = starting_array or []
    duplicate_values = set([])

    def get_unique_value(e):
        if attr is None:
            return e
        return get_attribute(e, attr)

    # Make sure the original starting array does not contain any duplicates.
    if len(flattened_array) != len(set([
            get_unique_value(c) for c in flattened_array])):
        raise exceptions.InvalidParamError(
            param='starting_array',
            message="The starting array must not contain any duplicates."
        )

    for a in array:
        value = get_unique_value(a)
        other_equal_values = [
            a for a in [get_unique_value(e) for e in flattened_array]
            if a == value
        ]
        # There should never be more than 1 other unique value so as long as
        # we guaranteed that the starting array does not contain duplicates.
        assert len(other_equal_values) in (0, 1), \
            "Detected duplicate values in the running array when they should " \
            "have been prevented by function logic."

        if other_equal_values:
            # Keep track of the values that were duplicated for logging purposes.
            duplicate_values.add(value)
            # If the prioritized callback is defined and it indicates that the
            # new value should not be prioritized, then we do not replace it
            # in the array - otherwise, we use the most recently defined value
            # (which is the default behavior).
            replace_in_array = True
            if prioritized is not None and prioritized(a) is False:
                replace_in_array = False
            # If the new value is prioritized, replace previous values with
            # the new one.  Otherwise, don't add the new value to the array.
            if replace_in_array:
                flattened_array = [
                    e for e in flattened_array
                    if get_unique_value(e) != value
                ] + [a]
        else:
            flattened_array.append(a)
    return flattened_array, duplicate_values


def remove_duplicates(array, **kwargs):
    """
    Removes duplicate instances of the provided `array` and issues appropriate
    logs when duplicates are found.

    Parameters:
    ----------
    array: :obj:`list` or :obj:`tuple`
        The primary iterable for which the duplicates are being removed.

    attr: :obj:`string` (optional)
        The attribute of the elements in each array that uniquely identifies
        one element from another.

        Default: None

    starting_array: :obj:`list` or :obj:`tuple` (optional)
        The iterable that the non-duplicate values of the primary `array`
        should be added to.  Only applicable when merging arrays.

        Default: None
    """
    from .strings import cjoin
    from .stdout import stdout

    attr = kwargs.pop('attr', None)
    log_duplicates = kwargs.pop('log_duplicates', True)
    starting_array = kwargs.pop('starting_array', None)

    flattened_array, duplicate_values = parse_duplicates(
        array=array,
        attr=attr,
        starting_array=starting_array
    )

    # If duplicate values were found in the original array, issue a warning
    # indicating that the duplicate values defined earlier were removed.
    if duplicate_values and log_duplicates:
        humanized = humanize_list(duplicate_values)
        intermediate_message = (
            f"in the array of {obj_name(array[0])} elements.")
        if starting_array is not None:
            intermediate_message = (
                f"between the original array of {obj_name(array[0])} elements "
                f"and the merging array of {obj_name(starting_array[0])} "
                "elements."
            )
        stdout.log(cjoin(
            f"Noticed duplicate value(s) {humanized}",
            cjoin.Conditional(
                f"for the attribute {attr}",
                attr is not None
            ),
            intermediate_message,
            "For each duplicate object, the object defined later in the "
            "array will be used."
        ))
    return flattened_array


def merge_without_duplicates(*args, **kwargs):
    """
    Merges the provided arrays together while removing duplicates in each
    individual array and the overall merged array.

    Parameters:
    ----------
    *args: arguments of type :obj:`list` or :obj:`tuple`
        A series of :obj:`list` or :obj:`tuple` arguments, which will be
        merged together into a single array.  Each array in the series will
        be filtered for duplicates and then merged together.

    attr: :obj:`string` (optional)
        The attribute of the elements in each array that uniquely identifies
        one element from another.

        Default: None
    """
    from git_blame_project import exceptions

    if len(args) == 0:
        raise exceptions.InvalidParamError(
            param='args',
            message="At least one argument must be provided."
        )
    flattened_array = remove_duplicates(args[0], **kwargs)
    for array in args[1:]:
        new_array = remove_duplicates(array, **kwargs)
        flattened_array = remove_duplicates(
            new_array, starting_array=flattened_array, **kwargs)
    return flattened_array

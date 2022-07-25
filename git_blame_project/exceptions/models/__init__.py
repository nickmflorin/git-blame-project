from git_blame_project import utils

from .exc_attribute import ExceptionAttribute  # noqa
from .exc_params import ExcParams  # noqa
from .formatter import Formatter  # noqa
from .mixins import *  # noqa


class StringFormatChoices:
    """
    It is often the case that an extension of :obj:`AbstractException` will
    define the an attribute that can be string formatted as an iterable of
    strings with formatting arguments in each one:

    >>> content = [
    >>>     "The {animal} jumped over the {object}.",
    >>>     "The {animal} jumped over something.",
    >>>     "Some animal jumped over something."
    >>> ]

    Then, the mechanics of the :obj:`AbstractException` will determine the
    value of the attribute based on a single string in the the iterable
    by looking for a string includes the optimal number of formatting arguments
    present on the instance and non-null.

    In other words, if we have an exception instance `e = MyException()` that
    defines the `content` attribute as shown above, if `e.animal` is not None
    but `e.object` is None, the second formatted string in the `content` array
    will be used.

    This optimal deterimination is made via the
    :obj:`git_blame_project.utils.conditionally_format_string` method.

    However, there are some cases where we only want the a subsection of the
    attribute array to be candidates for the eventual usage of the
    :obj:`git_blame_project.utils.conditionally_format_string` method.  That
    is, we only want them to be included as choices if a certain condition is
    met.

    In this case, the :obj:`StringFormatChoices` can be used to associate a set
    of choice strings with a conditional. If the conditional evaluates to True,
    the associated strings will be included in the overall candidate array.
    Additionally, if the instance specifies `isolated = True`, the choices
    associated with the :obj:`StringFormatChoices` instance will be the only
    choices included in the overall candidate array (instead of being appended
    to other defined choices).

    Parameters:
    ----------
    func: :obj:`lambda`
        A function that takes the current :obj:`AbstractException` instance as
        its first and only argument.  This function serves as the conditional
        for the :obj:`StringFormatChoices` instance.  If it evaluates to
        True, the `choices` on the :obj:`StringFormatChoices` instance will be
        included as string candidates.  Otherwise, they will not.

    choices: :obj:`str` or :obj:`tuple` or :obj:`list`
        A :obj:`str` or an iterable of :obj:`str` instances that should be
        included as candidates if the :obj:`StringFormatChoices` conditional
        evaluates to True.

    isolated: :obj:`bool` (optional)
        Whether or not the `choices` should be used as the only candidates when
        the :obj:`AbstractException` instance evaluates the most optimal choice
        of the overall set of choices.

        In other words, if `isolated` is True and the conditional of the
        :obj:`StringFormatChoices` instance evaluates to True, the `choices`
        of the :obj:`StringFormatChoices` instance will be the only candidates
        that are provided to the
         :obj:`git_blame_project.utils.conditionally_format_string` method.

        Default: False
    """
    def __init__(self, func, choices, isolated=False):
        self._func = func
        self._choices = choices
        self._isolated = isolated

    def __call__(self, instance):
        return self._func(instance) is True

    @property
    def choices(self):
        return utils.ensure_iterable(self._choices)

    @property
    def isolated(self):
        return self._isolated

    @classmethod
    def flattener(cls, instance):
        def fn(value):
            return cls.flatten(instance, value)
        return fn

    @classmethod
    def flatten(cls, instance, value):
        """
        Flattens a set of string choices that may include instances of
        :obj:`StringFormatChoices` to an array of :obj:`str` instances that
        represent the final candidates for the string formatting.
        """
        flattened = []
        for choice_value in value:
            if isinstance(choice_value, dict):
                choice_value = cls(**choice_value)
            # If the array value is an instance of StringFormatChoices, evaluate
            # the StringFormatChoices conditional to determine whether or not
            # the choices associated with the StringFormatChoices instance
            # should be included as candidates.
            if isinstance(choice_value, cls):
                if choice_value(instance) is True:
                    # If the :obj:`StringChoices` are isolated, they are the
                    # only choices for the overall content array in the case
                    # that the conditional is True.
                    if choice_value.isolated:
                        return choice_value.choices
                    flattened += choice_value.choices
            else:
                flattened += [choice_value]
        return flattened

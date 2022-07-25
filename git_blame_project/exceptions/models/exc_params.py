from abc import ABC

from git_blame_project import utils


class ExcParams(ABC):
    """
    Abstract base class that is meant to define the parameters that allow the
    class to construct an exception that should be raised under certain
    circumstances.

    Parameters:
    ----------
    exc_cls: :obj:`type` (optional)
        The exception class of the exception that the class should construct.

        Default: TypeError

    exc_message: :obj:`str` or :obj:`lambbda` (optional)
        The message of the exception that the class should construct.

        Can be provided as a :obj:`str` or a callback.  The callback should take
        a relevant instance as its first and only argument and return a string
        message.

    exc_kwargs: :obj:`dict` or :obj:`lambda` (optional)
        The keyword arguments that should be provided to the `exc_cls` when
        the class constructs the exception.

        Can be provided as a :obj:`dict` instance or a callback.  The callback
        should take a relevant instance as its first and only argument and
        return a :obj:`dict` instance.

        Default: {}
    """
    attrs = ['exc_cls', 'exc_kwargs', 'exc_message']

    def __init__(self, **kwargs):
        for attr in self.attrs:
            v = kwargs.pop(attr, None)
            setattr(self, f"_{attr}", v)

    @property
    def exc_cls(self):
        if isinstance(self._exc_cls, str):
            return utils.import_at_module_path(self._exc_cls)
        return self._exc_cls

    def exc_kwargs(self, instance):
        if self._exc_kwargs is not None \
                and hasattr(self.exc_kwargs, '__call__'):
            return self._exc_kwargs(instance)
        return self._exc_kwargs

    def exc_message(self, instance, **kwargs):
        # Providing the message directly should always take precedence over
        # every other source.  The message will be provided directly in the
        # case that the evaluation function returns a string error message.
        if 'message' in kwargs:
            return kwargs['message']
        # If the message was provided on initialization of the :obj:`Criteria`
        # instance or :obj:`check_instance` instance, use that.
        elif self._exc_message is not None:
            if utils.is_function(self._exc_message):
                return self._exc_message(instance)
            return self._exc_message
        # Finally, use the `default_message` parameter if it is provided.
        return kwargs.get(
            'default_message',
            "There was an error related to an instance of "
            f"{utils.obj_name(instance)}."
        )

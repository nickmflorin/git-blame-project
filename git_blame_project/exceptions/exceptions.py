from .base import AbstractException


class GitBlameProjectError(AbstractException):
    """
    Base class for all exceptions that may surface to the user, typically
    in a formatted form.
    """

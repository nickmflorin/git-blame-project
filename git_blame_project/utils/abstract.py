import collections

from .builtins import iterable_from_args


class ImmutableSequence(collections.abc.Sequence):
    def __init__(self, *args):
        self._store = iterable_from_args(*args)

    @property
    def data(self):
        return self._store

    def __getitem__(self, i):
        return self._store[i]

    def __len__(self):
        return len(self._store)

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


class MutableSequence(collections.abc.MutableSequence):
    def __init__(self, *args):
        self._store = iterable_from_args(*args, cast=list)

    @property
    def data(self):
        return self._store

    def merge(self, *args):
        data = self._store + iterable_from_args(*args, cast=list)
        return self.__class__(*data)

    def __getitem__(self, i):
        return self._store[i]

    def __len__(self):
        return len(self._store)

    def __setitem__(self, i, v):
        self._store.__setitem__(i, v)

    def __delitem__(self, i):
        self._store.__delitem__(i)

    def insert(self, i, v):
        self._store.insert(i, v)

import collections


class ImmutableSequence(collections.abc.Sequence):
    def __init__(self, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            self._store = args[0]
        else:
            self._store = list(args)

    @property
    def data(self):
        return self._store

    def __getitem__(self, i):
        return self._store[i]

    def __len__(self):
        return len(self._store)

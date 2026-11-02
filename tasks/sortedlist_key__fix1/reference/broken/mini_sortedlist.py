from bisect import bisect_left, bisect_right
from itertools import chain


def identity(value):
    return value


class SortedList:
    DEFAULT_LOAD_FACTOR = 1000

    def __new__(cls, iterable=None, key=None):
        if key is None:
            return object.__new__(cls)
        if cls is SortedList:
            cls = SortedKeyList
        return object.__new__(cls)

    def __init__(self, iterable=None, key=None):
        assert key is None
        self._setup(None, iterable)

    def _setup(self, key, iterable):
        self._len = 0
        self._load = self.DEFAULT_LOAD_FACTOR
        self._lists, self._maxes, self._index, self._offset = [], [], [], 0
        self._key_fn = key
        self._keys = self._lists if key is None else []
        if iterable is not None:
            self.update(iterable)

    @property
    def key(self):
        return self._key_fn

    def _kv(self, value):
        return value if self._key_fn is None else self._key_fn(value)

    def _sep(self):
        return self._keys is not self._lists

    def _clear_data(self):
        del self._lists[:], self._maxes[:], self._index[:]
        if self._sep():
            del self._keys[:]
        self._len = 0

    clear = _clear_data

    def add(self, value):
        k = self._kv(value)
        if self._maxes:
            pos = bisect_right(self._maxes, k)
            if pos == len(self._maxes):
                pos -= 1
                self._lists[pos].append(value)
                if self._sep():
                    self._keys[pos].append(k)
                self._maxes[pos] = k
            else:
                idx = bisect_right(self._keys[pos], k)
                self._lists[pos].insert(idx, value)
                if self._sep():
                    self._keys[pos].insert(idx, k)
            self._expand(pos)
        else:
            self._lists.append([value])
            self._maxes.append(k)
            if self._sep():
                self._keys.append([k])
        self._len += 1

    def _expand(self, pos):
        load = self._load
        if len(self._lists[pos]) > (load << 1):
            half = self._lists[pos][load:]
            del self._lists[pos][load:]
            if self._sep():
                khalf = self._keys[pos][load:]
                del self._keys[pos][load:]
                self._keys.insert(pos + 1, khalf)
            else:
                khalf = half
            self._maxes[pos] = self._keys[pos][-1]
            self._lists.insert(pos + 1, half)
            self._maxes.insert(pos + 1, khalf[-1])
            del self._index[:]

    def update(self, iterable):
        values = sorted(iterable, key=self._key_fn)
        if self._maxes:
            if len(values) * 4 >= self._len:
                values = sorted(chain(chain.from_iterable(self._lists), values), key=self._key_fn)
                self._clear_data()
            else:
                for v in values:
                    self.add(v)
                return
        load = self._load
        self._lists.extend(values[p:p + load] for p in range(0, len(values), load))
        if self._sep():
            self._keys.extend([self._key_fn(v) for v in sub] for sub in self._lists)
        self._maxes.extend(sub[-1] for sub in self._keys)
        self._len = len(values)
        del self._index[:]

    _update = update

    def __len__(self):
        return self._len

    def _find(self, value):
        """Return (pos, idx) of the first stored item equal to value, or None."""
        k = self._kv(value)
        if not self._maxes:
            return None
        pos = bisect_left(self._maxes, k)
        if pos == len(self._maxes):
            return None
        idx = bisect_left(self._keys[pos], k)
        while True:
            if self._keys[pos][idx] != k:
                return None
            if self._lists[pos][idx] == value:
                return pos, idx
            idx += 1
            if idx == len(self._keys[pos]):
                pos, idx = pos + 1, 0
                if pos == len(self._maxes):
                    return None

    def __contains__(self, value):
        return self._find(value) is not None

    def discard(self, value):
        found = self._find(value)
        if found:
            self._delete(*found)

    def remove(self, value):
        found = self._find(value)
        if not found:
            raise ValueError('{0!r} not in list'.format(value))
        self._delete(*found)

    def _delete(self, pos, idx):
        del self._lists[pos][idx]
        if self._sep():
            del self._keys[pos][idx]
        keys_pos = self._keys[pos]
        self._len -= 1
        n = len(keys_pos)
        if n > (self._load >> 1):
            self._maxes[pos] = keys_pos[-1]
        elif len(self._lists) > 1:
            if not pos:
                pos += 1
            prev = pos - 1
            self._lists[prev].extend(self._lists[pos])
            if self._sep():
                self._keys[prev].extend(self._keys[pos])
                del self._keys[pos]
            self._maxes[prev] = self._keys[prev][-1]
            del self._lists[pos]
            del self._maxes[pos]
            del self._index[:]
            self._expand(prev)
        elif n:
            self._maxes[pos] = keys_pos[-1]
        else:
            del self._lists[pos]
            if self._sep():
                del self._keys[pos]
            del self._maxes[pos]
            del self._index[:]

    def _pos(self, idx):
        for pos, sub in enumerate(self._lists):
            if idx < len(sub):
                return pos, idx
            idx -= len(sub)
        raise IndexError('list index out of range')

    def _global(self, pos, idx):
        return sum(map(len, self._lists[:pos])) + idx

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self._len)
            if step == 1:
                return list(self.islice(start, stop))
            return [self[i] for i in range(start, stop, step)]
        if index < 0:
            index += self._len
        if not 0 <= index < self._len:
            raise IndexError('list index out of range')
        pos, idx = self._pos(index)
        return self._lists[pos][idx]

    def __delitem__(self, index):
        if isinstance(index, slice):
            for i in sorted(range(*index.indices(self._len)), reverse=True):
                del self[i]
            return
        if index < 0:
            index += self._len
        if not 0 <= index < self._len:
            raise IndexError('list index out of range')
        self._delete(*self._pos(index))

    def __iter__(self):
        return chain.from_iterable(self._lists)

    def __reversed__(self):
        return chain.from_iterable(map(reversed, reversed(self._lists)))

    def pop(self, index=-1):
        if not self._len:
            raise IndexError('pop index out of range')
        if index < 0:
            index += self._len
        if not 0 <= index < self._len:
            raise IndexError('pop index out of range')
        pos, idx = self._pos(index)
        value = self._lists[pos][idx]
        self._delete(pos, idx)
        return value

    def _bk_left(self, k):
        pos = bisect_left(self._maxes, k)
        if pos == len(self._maxes):
            return self._len
        return self._global(pos, bisect_left(self._keys[pos], k))

    def _bk_right(self, k):
        pos = bisect_right(self._maxes, k)
        if pos == len(self._maxes):
            return self._len
        return self._global(pos, bisect_right(self._keys[pos], k))

    def bisect_left(self, value):
        return self._bk_left(self._kv(value))

    def bisect_right(self, value):
        return self._bk_right(self._kv(value))

    bisect = bisect_right

    def count(self, value):
        k = self._kv(value)
        if not self._maxes:
            return 0
        pos = bisect_left(self._maxes, k)
        if pos == len(self._maxes):
            return 0
        idx, total = bisect_left(self._keys[pos], k), 0
        while pos < len(self._maxes):
            keys, sub = self._keys[pos], self._lists[pos]
            while idx < len(keys) and keys[idx] == k:
                total += sub[idx] == value
                idx += 1
            if idx < len(keys):
                break
            pos, idx = pos + 1, 0
        return total

    def index(self, value, start=None, stop=None):
        n = self._len
        start = 0 if start is None else start
        if start < 0:
            start = max(start + n, 0)
        stop = n if stop is None else stop
        if stop < 0:
            stop += n
        stop = min(stop, n)
        if n and start < stop:
            k = self._kv(value)
            first = max(start, self._bk_left(k))
            for i, item in enumerate(self.islice(first, stop), start=first):
                if self._kv(item) != k:
                    break
                if item == value:
                    return i
        raise ValueError('{0!r} is not in list'.format(value))

    def islice(self, start=None, stop=None, reverse=False):
        start, stop, _ = slice(start, stop).indices(self._len)
        if start >= stop:
            return iter(())
        pos, idx = self._pos(start)

        def forward():
            nonlocal pos, idx
            for _ in range(stop - start):
                yield self._lists[pos][idx]
                idx += 1
                if idx == len(self._lists[pos]):
                    pos, idx = pos + 1, 0

        return iter(list(forward())[::-1]) if reverse else forward()

    def _irange_key(self, min_key, max_key, inclusive, reverse):
        if not self._maxes:
            return iter(())
        min_inc, max_inc = inclusive
        start = 0 if min_key is None else (self._bk_left if min_inc else self._bk_right)(min_key)
        stop = self._len if max_key is None else (self._bk_left if max_inc else self._bk_right)(max_key)
        return self.islice(start, stop, reverse)

    def irange(self, minimum=None, maximum=None, inclusive=(True, True), reverse=False):
        lo = None if minimum is None else self._kv(minimum)
        hi = None if maximum is None else self._kv(maximum)
        return self._irange_key(lo, hi, inclusive, reverse)

    def _new(self, values):
        return self.__class__(values)

    def copy(self):
        return self._new(self)

    __copy__ = copy

    def __add__(self, other):
        return self._new(list(self) + list(other))

    __radd__ = __add__

    def __iadd__(self, other):
        self.update(other)
        return self

    def __eq__(self, other):
        if not hasattr(other, '__len__') or isinstance(other, (str, bytes)):
            return NotImplemented
        return list(self) == list(other)

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    __hash__ = None

    def __repr__(self):
        return '{0}({1!r})'.format(type(self).__name__, list(self))

    def append(self, value):
        raise NotImplementedError('use ``sl.add(value)`` instead')

    def extend(self, values):
        raise NotImplementedError('use ``sl.update(values)`` instead')

    def insert(self, index, value):
        raise NotImplementedError('use ``sl.add(value)`` instead')

    def reverse(self):
        raise NotImplementedError('use ``reversed(sl)`` instead')

    def __setitem__(self, index, value):
        raise NotImplementedError('use ``del sl[index]`` and ``sl.add(value)`` instead')


class SortedKeyList(SortedList):
    def __new__(cls, iterable=None, key=identity):
        return object.__new__(cls)

    def __init__(self, iterable=None, key=identity):
        self._setup(key, iterable)

    def _new(self, values):
        return self.__class__(values, key=self._key_fn)

    def bisect_key_left(self, key):
        return self._bk_left(key)

    def bisect_key_right(self, key):
        return self._bk_right(key)

    bisect_key = bisect_key_right

    def irange_key(self, min_key=None, max_key=None, inclusive=(True, True), reverse=False):
        return self._irange_key(min_key, max_key, inclusive, reverse)

    def __repr__(self):
        return '{0}({1!r}, key={2!r})'.format(type(self).__name__, list(self), self._key_fn)

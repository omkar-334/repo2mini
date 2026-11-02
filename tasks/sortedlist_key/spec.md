# Task: mini SortedList with SortedKeyList

Implement `solution/mini_sortedlist.py`, a compact standalone re-implementation of the `SortedList` class from the `sortedcontainers` library. Use only the Python standard library. Do **not** import `sortedcontainers`.

Follow the original library's public API **and its internal layout**:

* `SortedList(iterable=None)` keeps its values in sorted order. Class attribute `DEFAULT_LOAD_FACTOR = 1000`.
* Internal state uses the original names: `_lists` (a list of sorted sublists), `_maxes` (the last value of every sublist), `_len`, `_load` (set from `DEFAULT_LOAD_FACTOR`), plus `_index` (a list) and `_offset`. A new list built from an iterable is split into sublists of `_load` values. Adding a value that makes a sublist longer than twice `_load` splits it in two at `_load`. Deleting values shrinks sublists and merges a sublist into its neighbour once it falls to `_load >> 1` values or fewer (while more than one sublist exists), following the original's rules.
* Methods: `add`, `update`, `clear`, `discard` (silent), `remove` (raises `ValueError`), `pop(index=-1)`, `index(value, start=None, stop=None)`, `count`, `bisect_left`, `bisect_right`, `bisect` (alias of `bisect_right`), `islice(start=None, stop=None, reverse=False)`, `irange(minimum=None, maximum=None, inclusive=(True, True), reverse=False)`, `copy`.
* Sequence behaviour: `len`, `in`, iteration, `reversed`, indexing with ints (negative allowed, `IndexError` out of range) and slices (including steps), `del sl[i]` and `del sl[i:j]`, `+`, `+=`, `==`, `!=`, and `repr` in the form `SortedList([1, 2, 3])`.
* Operations that would break the ordering (`append`, `extend`, `insert`, `reverse`, item assignment) raise `NotImplementedError`.
* `irange` and `islice` return iterators.

## Additional requirements for this task: key functions

Also support the original library's key based sorting, in the same module:

* `SortedKeyList(iterable=None, key=identity)` is a subclass of `SortedList` that keeps values ordered by `key(value)`. It has a `key` property, a parallel `_keys` structure (a list of sublists of keys, shaped like `_lists`), and `_maxes` holds the last **key** of each sublist.
* `SortedList(iterable, key=some_function)` (with a non-`None` key) returns a `SortedKeyList` instance, as in the original. `SortedList(...).key` is `None`.
* `SortedKeyList` adds `bisect_key_left(key)`, `bisect_key_right(key)` (alias `bisect_key`) and `irange_key(min_key=None, max_key=None, inclusive=(True, True), reverse=False)`. Its `bisect_left`, `bisect_right`, `irange`, `count`, `index`, `remove`, `discard` and `update` take values and compare them through the key. `copy()` and `+` keep the key.
* `repr` of a `SortedKeyList` is `SortedKeyList([...], key=<key>)`.

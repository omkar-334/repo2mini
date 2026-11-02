from mini_sortedlist import SortedList


def test_sorted_on_init():
    assert list(SortedList([3, 1, 2])) == [1, 2, 3]


def test_add_and_len():
    sl = SortedList()
    for v in (5, 1, 3):
        sl.add(v)
    assert list(sl) == [1, 3, 5] and len(sl) == 3


def test_repr():
    assert repr(SortedList([2, 1])) == "SortedList([1, 2])"

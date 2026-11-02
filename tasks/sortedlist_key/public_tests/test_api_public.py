from mini_sortedlist import SortedKeyList, SortedList


def test_key_sorting():
    sl = SortedList([3, 1, 2], key=lambda x: -x)
    assert list(sl) == [3, 2, 1] and isinstance(sl, SortedKeyList)


def test_plain_key_is_none():
    assert SortedList([1]).key is None


def test_key_property():
    f = len
    assert SortedKeyList(["aa", "b"], key=f).key is f

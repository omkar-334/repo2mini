from mini_cut import cut


def test_basic_right_closed():
    codes, cats = cut([1, 5, 10], [0, 5, 10])
    assert list(codes) == [0, 0, 1] and cats == ["(0, 5]", "(5, 10]"]


def test_outside_is_minus_one():
    codes, _ = cut([-1, 3, 20], [0, 5, 10])
    assert list(codes) == [-1, 0, -1]


def test_custom_labels():
    codes, cats = cut([1, 7], [0, 5, 10], labels=["lo", "hi"])
    assert list(codes) == [0, 1] and cats == ["lo", "hi"]

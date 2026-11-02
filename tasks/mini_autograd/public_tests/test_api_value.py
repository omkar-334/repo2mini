from mini_autograd import Value


def test_attributes():
    v = Value(2)
    assert v.data == 2.0 and v.grad == 0.0 and isinstance(v._prev, set)


def test_simple_backward():
    x, y = Value(3.0), Value(4.0)
    z = x * y + x
    z.backward()
    assert abs(x.grad - 5.0) < 1e-9 and abs(y.grad - 3.0) < 1e-9


def test_methods_exist():
    v = Value(0.5)
    for m in ("tanh", "relu", "exp", "log", "backward"):
        assert callable(getattr(v, m))

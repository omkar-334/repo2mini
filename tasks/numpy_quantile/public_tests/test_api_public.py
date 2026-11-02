import numpy as np
from mini_quantile import percentile, quantile


def test_median_linear():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5


def test_percentile_array():
    out = percentile([1, 2, 3, 4, 5], [0.0, 100.0])
    assert list(out) == [1.0, 5.0]


def test_invalid_q():
    try:
        quantile([1, 2], 1.5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")

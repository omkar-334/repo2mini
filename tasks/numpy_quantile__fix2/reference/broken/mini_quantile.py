import numpy as np

# method name -> (virtual index function of (n, q), gamma fixer or None). Integer valued virtual indexes mean no interpolation.
def _virtual(alpha, beta):
    return lambda n, q: n * q + (alpha + q * (1 - alpha - beta)) - 1


def _closest(n, q):
    """Nearest order statistic; an exact tie goes to the even (1 based) order statistic."""
    v = n * q - 1 - 0.5
    prev = np.floor(v)
    return np.where((v - prev == 0) & (prev % 2 == 1), prev, prev + 1).astype(np.intp)


METHODS = {
    "inverted_cdf": (lambda n, q: np.ceil(n * q - 1).astype(np.intp), None),
    "averaged_inverted_cdf": (lambda n, q: n * q - 1, lambda g, _: (1 + (g > 0)) / 2),
    "closest_observation": (_closest, None),
    "interpolated_inverted_cdf": (_virtual(0, 1), lambda g, _: g),
    "hazen": (_virtual(0.5, 0.0), lambda g, _: g),
    "weibull": (_virtual(0, 0), lambda g, _: g),
    "linear": (lambda n, q: (n - 1) * q, lambda g, _: g),
    "median_unbiased": (_virtual(1 / 3, 1 / 3), lambda g, _: g),
    "normal_unbiased": (_virtual(3 / 8, 3 / 8), lambda g, _: g),
    "lower": (lambda n, q: np.floor((n - 1) * q).astype(np.intp), None),
    "higher": (lambda n, q: np.ceil((n - 1) * q).astype(np.intp), None),
    "midpoint": (lambda n, q: 0.5 * (np.floor((n - 1) * q) + np.ceil((n - 1) * q)), lambda g, _: np.where(g == 0, 0.0, 0.5)),
    "nearest": (lambda n, q: np.around((n - 1) * q).astype(np.intp), None),
}


def _lerp(a, b, t):
    diff = np.subtract(b, a)
    out = np.asanyarray(np.add(a, diff * t))
    np.subtract(b, diff * (1 - t), out=out, where=t >= 0.5)
    return out


def quantile(a, q, axis=None, method="linear", keepdims=False):
    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")
    q = np.asanyarray(q)
    if q.dtype.kind == "c":
        raise TypeError("q must be a real number")
    q = q.astype(np.float64) if q.dtype.kind != "f" else q
    if not ((0 <= q).all() and (q <= 1).all()):
        raise ValueError("Quantiles must be in the range [0, 1]")
    if method not in METHODS:
        raise ValueError(f"{method!r} is not a valid method. Use one of: {list(METHODS)}")
    a_ndim = a.ndim
    if axis is None:
        arr, ax = a.reshape(-1), 0
    else:
        ax = axis + a_ndim if axis < 0 else axis
        if not 0 <= ax < a_ndim:
            raise np.exceptions.AxisError(axis, a_ndim)
        arr = np.moveaxis(a, ax, 0)
    arr = np.sort(arr, axis=0)
    n = arr.shape[0]
    vfn, fix = METHODS[method]
    virtual = np.asanyarray(vfn(n, q))
    if fix is None:
        idx = np.clip(virtual, 0, n - 1)
        result = arr[idx]
    else:
        virtual = virtual.astype(np.float64)
        prev = np.asanyarray(np.floor(virtual))
        nxt = np.asanyarray(prev + 1)
        above = virtual >= n - 1
        if above.any():
            prev[above] = n - 1
            nxt[above] = n - 1
        below = virtual < 0
        if below.any():
            prev[below] = 0
            nxt[below] = 0
        gamma = np.asanyarray(fix(np.asanyarray(virtual - prev), virtual), dtype=virtual.dtype)
        prev, nxt = prev.astype(np.intp), nxt.astype(np.intp)
        pv, nv = arr[prev], arr[nxt]
        g = gamma.reshape(gamma.shape + (1,) * (pv.ndim - gamma.ndim))
        result = _lerp(pv, nv, g)
    if arr.dtype.kind in "fc":
        has_nan = np.isnan(arr[-1])
        if np.any(has_nan):
            result = np.where(has_nan, np.nan, result)
    if keepdims:
        if axis is None:
            result = result.reshape(q.shape + (1,) * a_ndim)
        else:
            result = np.expand_dims(result, q.ndim + ax)
    if isinstance(result, np.ndarray) and result.ndim == 0:
        result = result[()]
    return result


def percentile(a, q, axis=None, method="linear", keepdims=False):
    q = np.true_divide(np.asanyarray(q), 100)
    return quantile(a, q, axis=axis, method=method, keepdims=keepdims)

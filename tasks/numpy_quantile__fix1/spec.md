# Task: mini np.quantile

Implement `solution/mini_quantile.py`, a standalone re-implementation of NumPy's `quantile` and `percentile` for real valued arrays. You may use NumPy for array operations (`sort`, `floor`, `take`, and so on), but you must **not** call `np.quantile`, `np.percentile`, `np.nanquantile`, `np.nanpercentile` or `np.median`, and must not import NumPy's private function base module.

Required interface, matching the original:

* `quantile(a, q, axis=None, method="linear", keepdims=False)` and `percentile(a, q, axis=None, method="linear", keepdims=False)` (`q` in percent). `q` is a float or an array of floats; `axis` is `None` or an int (negative allowed).
* All thirteen `method` values of the original: `inverted_cdf`, `averaged_inverted_cdf`, `closest_observation`, `interpolated_inverted_cdf`, `hazen`, `weibull`, `linear`, `median_unbiased`, `normal_unbiased`, `lower`, `higher`, `midpoint`, `nearest`. An unknown method raises `ValueError`.
* Same output shape rules as the original: a scalar `q` removes the reduced axis, an array `q` adds its dimensions in front, and `keepdims=True` keeps the reduced axis with length 1 (after the dimensions of `q`).
* Same output dtype rules as the original, including which methods return a value of the input dtype for integer input and which interpolate and return floats.
* NaN handling as in the original: if a reduced slice contains NaN, its result is NaN.
* `q` outside `[0, 1]` (or `[0, 100]` for `percentile`) raises `ValueError`. Complex input raises `TypeError`.

Keep the implementation compact and readable.

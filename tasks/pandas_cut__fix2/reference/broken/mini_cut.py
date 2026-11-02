import numpy as np


def _round_frac(x, precision):
    if not np.isfinite(x) or x == 0:
        return x
    frac, whole = np.modf(x)
    digits = -int(np.floor(np.log10(abs(frac)))) - 1 + precision if whole == 0 else precision
    return np.around(x, digits)


def _infer_precision(base, bins):
    for p in range(base, 20):
        if np.unique(np.asarray([_round_frac(b, p) for b in bins])).size == bins.size:
            return p
    return base


def _nbins_to_bins(x, nbins, right):
    if nbins < 1:
        raise ValueError("`bins` should be a positive integer.")
    if x.size == 0:
        raise ValueError("Cannot cut empty array")
    mn, mx = x.min(), x.max()
    if np.isinf(mn) or np.isinf(mx):
        raise ValueError("cannot specify integer `bins` when input data contains infinity")
    if mn == mx:
        mn -= 0.001 * abs(mn) if mn != 0 else 0.001
        mx += 0.001 * abs(mx) if mx != 0 else 0.001
        return np.linspace(mn, mx, nbins + 1, endpoint=True)
    bins = np.linspace(mn, mx, nbins + 1, endpoint=True)
    adj = (mx - mn) * 0.001
    if right:
        bins[-1] += adj
    else:
        bins[0] -= adj
    return bins


def cut(x, bins, right=True, labels=None, precision=3, include_lowest=False, duplicates="raise"):
    """Returns (codes, categories). codes is -1 for NaN/out of range; categories is a list of labels (or None if labels=False)."""
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError("Input array must be 1 dimensional")
    x = x.astype(np.float64) if x.dtype.kind in "iub" and np.isscalar(bins) else x
    if np.isscalar(bins):
        bins = _nbins_to_bins(x[~np.isnan(x.astype(float))] if x.dtype.kind == "f" else x, int(bins), right)
    else:
        bins = np.asarray(bins)
        if bins.ndim != 1 or bins.size == 0:
            raise ValueError("bins must be a non empty 1 dimensional sequence")
        if (np.diff(bins) < 0).any():
            raise ValueError("bins must increase monotonically.")
    if duplicates not in ("raise", "drop"):
        raise ValueError("invalid value for 'duplicates' parameter, valid options are: raise, drop")
    unique_bins = np.unique(bins)
    if len(unique_bins) < len(bins) and len(bins) != 2:
        if duplicates == "raise":
            raise ValueError(f"Bin edges must be unique: {bins!r}.\nYou can drop duplicate edges by setting the 'duplicates' kwarg")
        bins = unique_bins
    side = "left" if right else "right"
    xf = x.astype(np.float64)
    ids = bins.searchsorted(xf, side=side)
    if include_lowest:
        ids[xf == bins[0]] = 1
    na = np.isnan(xf) | (ids == len(bins)) | (ids == 0)
    codes = np.where(na, -1, ids - 1)
    if labels is False:
        return codes, None
    if labels is None:
        p = _infer_precision(precision, bins)
        breaks = [_round_frac(b, p) for b in bins]
        if right and include_lowest:
            breaks[0] = breaks[0] - 10 ** (-p)
            breaks = [np.float64(b) for b in breaks]
        lo, hi = ("(", "]") if right else ("[", ")")
        cats = [f"{lo}{breaks[i]}, {breaks[i + 1]}{hi}" for i in range(len(breaks) - 1)]
    else:
        labels = list(labels)
        if len(labels) != len(bins) - 1:
            raise ValueError("Bin labels must be one fewer than the number of bin edges")
        if len(set(labels)) != len(labels):
            raise ValueError("labels must be unique")
        cats = labels
    return codes, cats

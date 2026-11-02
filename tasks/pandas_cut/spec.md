# Task: mini pd.cut

Implement `solution/mini_cut.py`, a standalone re-implementation of the binning logic of `pandas.cut` for one dimensional numeric data. Use NumPy only. Do **not** import `pandas`.

Interface:

`cut(x, bins, right=True, labels=None, precision=3, include_lowest=False, duplicates="raise")` returns a tuple `(codes, categories)`:

* `codes`: an integer NumPy array with one entry per element of `x`: the zero based index of the bin it falls into, or `-1` when the value is NaN or outside all bins.
* `categories`: a list of strings, one per bin, formatted exactly like `str(interval)` of the categories that `pandas.cut` produces, for example `"(0.0, 1.5]"` or `"[0, 5)"`. If `labels` is a list, `categories` is that list (as given). If `labels=False`, `categories` is `None`.

Behaviour to match the original:

* `bins` is either an int (the number of equal width bins) or a monotonically increasing sequence of edges. An int is turned into edges the way the original does it, including its small adjustment of one end so that the extreme value is included.
* `right` selects whether bins are closed on the right (the default) or left. `include_lowest` makes the first interval include its left edge.
* `precision` controls how many decimals appear in the labels. The original increases the precision when rounding would make neighbouring edges look identical, and it formats the first label specially when `right` and `include_lowest` are both set.
* `duplicates="raise"` raises `ValueError` for repeated edges, `"drop"` removes them.
* `ValueError` for: non increasing `bins`, `bins` below 1, empty input with an int `bins`, int `bins` with infinite data, a wrong number of `labels`, non unique `labels`, input that is not one dimensional.

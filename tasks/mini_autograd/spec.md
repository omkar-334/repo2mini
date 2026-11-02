# Task: mini autograd

Implement `solution/mini_autograd.py` with a scalar reverse mode automatic differentiation engine.

Required interface:

* `Value(data, _children=(), _op="")` with attributes `data` (float), `grad` (float, starts at 0.0), `_prev` (set of child Values), `_op` (str).
* Operators `+`, `-`, `*`, `/`, unary `-`, `**` (int or float exponent), including reflected forms with plain numbers (`2 * v`, `1 - v`, `3 / v`).
* Methods `tanh()`, `relu()`, `exp()`, `log()`.
* `backward()` computes gradients of this value with respect to all upstream values, accumulating into `.grad`.

Requirements: gradients must accumulate correctly when a value is used more than once, and `backward()` must handle very deep graphs (thousands of chained operations) without recursion errors.

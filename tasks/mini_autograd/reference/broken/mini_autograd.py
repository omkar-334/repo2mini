import math


class Value:
    def __init__(self, data, _children=(), _op=""):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _b():
            self.grad = out.grad
            other.grad = out.grad

        out._backward = _b
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _b():
            self.grad = other.data * out.grad
            other.grad = self.data * out.grad

        out._backward = _b
        return out

    def __pow__(self, k):
        assert isinstance(k, (int, float))
        out = Value(self.data ** k, (self,), f"**{k}")

        def _b():
            self.grad = k * self.data ** (k - 1) * out.grad

        out._backward = _b
        return out

    def exp(self):
        out = Value(math.exp(self.data), (self,), "exp")

        def _b():
            self.grad = out.data * out.grad

        out._backward = _b
        return out

    def log(self):
        out = Value(math.log(self.data), (self,), "log")

        def _b():
            self.grad = out.grad / self.data

        out._backward = _b
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _b():
            self.grad = (1 - t * t) * out.grad

        out._backward = _b
        return out

    def relu(self):
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")

        def _b():
            self.grad = (out.data > 0) * out.grad

        out._backward = _b
        return out

    def backward(self):
        topo, seen, stack = [], set(), [(self, False)]
        while stack:
            node, done = stack.pop()
            if done:
                topo.append(node)
                continue
            if node in seen:
                continue
            seen.add(node)
            stack.append((node, True))
            for c in node._prev:
                if c not in seen:
                    stack.append((c, False))
        self.grad = 1.0
        for node in reversed(topo):
            node._backward()

    def __neg__(self):
        return self * -1

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return self * other ** -1

    def __rtruediv__(self, other):
        return other * self ** -1

    def __repr__(self):
        return f"Value(data={self.data}, grad={self.grad})"

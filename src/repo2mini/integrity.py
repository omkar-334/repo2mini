"""AST based integrity check: a solution must not import, call or execute the original library.

Mentions in comments, docstrings and strings are fine. What counts: importing a banned module, calling a banned function such as
`np.quantile`, and dynamic code loading (`exec`, `eval`, `compile`, `__import__`, `importlib`, `runpy`). Violating runs are disqualified.
"""
from __future__ import annotations

import ast

DYNAMIC_NAMES = {"exec", "eval", "compile", "__import__"}
DYNAMIC_MODULES = {"importlib", "runpy"}


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def check(files: dict[str, str], cfg: dict) -> list[str]:
    banned_imports = set(cfg.get("banned_imports", []))
    banned_calls = set(cfg.get("banned_calls", []))
    out: list[str] = []
    for path, src in files.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.split(".")[0] in banned_imports | DYNAMIC_MODULES or any(a.name.startswith(b) for b in banned_calls):
                        out.append(f"{path}: import {a.name}")
            elif isinstance(n, ast.ImportFrom):
                mod = n.module or ""
                if mod.split(".")[0] in banned_imports | DYNAMIC_MODULES or any(mod.startswith(b) for b in banned_calls):
                    out.append(f"{path}: from {mod} import ...")
                for a in n.names:
                    if f"{mod}.{a.name}" in banned_calls:
                        out.append(f"{path}: from {mod} import {a.name}")
            elif isinstance(n, ast.Call):
                name = _dotted(n.func)
                if isinstance(n.func, ast.Name) and n.func.id in DYNAMIC_NAMES:
                    out.append(f"{path}: call {n.func.id}()")
                elif name in banned_calls or (name.replace("np.", "numpy.", 1) in banned_calls):
                    out.append(f"{path}: call {name}()")
    return sorted(set(out))

"""Own minimal read only repo tools (grep, read_file, list_dir, git_log), jailed to one repo root.

Chosen over MCP servers or an external agent: identical behavior across providers, every call is logged,
and no extra dependency or permission surface. Exposed as OpenAI function calling schemas.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

MAX_OUT = 8000


class RepoTools:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _safe(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError("path escapes repo root")
        return p

    def _clip(self, s: str) -> str:
        return s if len(s) <= MAX_OUT else s[:MAX_OUT] + f"\n...[truncated {len(s) - MAX_OUT} chars]"

    def grep(self, pattern: str, path: str = ".", max_results: int = 50) -> str:
        p = self._safe(path)
        r = subprocess.run(["grep", "-rIn", "-m", "5", "--", pattern, str(p)], capture_output=True, text=True, timeout=30)
        lines = [l.replace(str(self.root) + "/", "") for l in r.stdout.splitlines()[:max_results]]
        return self._clip("\n".join(lines) or "no matches")

    def read_file(self, path: str, start: int = 1, end: int = 200) -> str:
        lines = self._safe(path).read_text(errors="replace").splitlines()
        sel = lines[max(start - 1, 0):end]
        return self._clip("\n".join(f"{i}: {l}" for i, l in enumerate(sel, start=max(start, 1))))

    def list_dir(self, path: str = ".") -> str:
        p = self._safe(path)
        return self._clip("\n".join(sorted(f"{c.name}{'/' if c.is_dir() else ''}" for c in p.iterdir() if c.name != ".git")))

    def git_log(self, path: str = ".", n: int = 10) -> str:
        r = subprocess.run(["git", "-C", str(self.root), "log", f"-{min(n, 30)}", "--oneline", "--", str(self._safe(path))],
                           capture_output=True, text=True, timeout=30)
        return self._clip(r.stdout or r.stderr or "no history")

    def call(self, name: str, args: dict) -> str:
        try:
            if name not in {"grep", "read_file", "list_dir", "git_log"}:
                return (f"error: there is no tool named {name!r}. The only tools are grep, read_file, list_dir and git_log. "
                        "To deliver your solution, write the files as plain text in your reply (FILE: solution/<name>.py then a code block), not in a tool call.")
            return getattr(self, name)(**args)
        except Exception as e:
            return f"error: {e}"


SCHEMAS = [
    {"type": "function", "function": {"name": "grep", "description": "Search repo files for a regex.",
     "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read lines of a file.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "list_dir", "description": "List a directory.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "git_log", "description": "Recent commits touching a path.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "n": {"type": "integer"}}}}},
]

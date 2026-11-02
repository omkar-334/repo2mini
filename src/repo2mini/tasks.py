"""Task loading, file parsing and context building. Hidden tests are never read by prompt builders."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
REPOS_DIR = ROOT / "repos"

FORMAT = """Return your implementation as one or more files. Each file must be preceded by a line
`FILE: solution/<name>.py` and then a fenced code block with the full file contents. Use only the Python
standard library unless the task says otherwise. Do not include any other file paths."""

FILE_HDR = re.compile(r"^[ \t]*(?:\*\*|`)?FILE:[ \t]*(solution/[\w./-]+?)(?:\*\*|`)?[ \t]*$", re.MULTILINE)


@dataclass
class Task:
    id: str
    root: Path
    meta: dict

    @property
    def spec(self) -> str:
        return (self.root / "spec.md").read_text()


def load_task(task_id: str) -> Task:
    root = TASKS_DIR / task_id
    meta = json.loads((root / "task.json").read_text())
    return Task(id=task_id, root=root, meta=meta)


def list_tasks() -> list[str]:
    return sorted(p.name for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def parse_files(text: str) -> dict[str, str]:
    """Split on `FILE: solution/<name>` headers. The code may sit in a fenced block, or the opening fence may be missing."""
    files: dict[str, str] = {}
    heads = list(FILE_HDR.finditer(text))
    for i, m in enumerate(heads):
        path = m.group(1)
        if ".." in path.split("/") or path.startswith("/"):
            continue
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip("\n")
        lines = body.split("\n")
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        for j, ln in enumerate(lines):
            if ln.strip() == "```":
                lines = lines[:j]
                break
        code = "\n".join(lines).rstrip() + "\n"
        if code.strip():
            files[path] = code
    return files


def approx_tokens(s: str) -> int:
    return len(s) // 4


def build_context(task: Task, level: str, max_tokens: int = 400_000) -> tuple[str, dict]:
    """L0 is empty. Higher levels list globs in task.json under context.<level>, paths relative to repos/<repo>."""
    info = {"level": level, "files": 0, "tokens": 0, "truncated": False}
    if level in ("L0", "AG"):
        return "", info
    spec = task.meta.get("context", {}).get(level)
    if not spec:
        raise ValueError(f"task {task.id} has no context for {level}")
    repo = REPOS_DIR / task.meta["repo"]
    seen, parts, total = set(), [], 0
    for pattern in spec:
        for f in sorted(repo.glob(pattern)):
            if not f.is_file() or f in seen:
                continue
            seen.add(f)
            try:
                txt = f.read_text()
            except UnicodeDecodeError:
                continue
            t = approx_tokens(txt)
            if total + t > max_tokens:
                info["truncated"] = True
                continue
            parts.append(f"=== {f.relative_to(repo)} ===\n{txt}")
            total += t
    info.update(files=len(parts), tokens=total)
    return "\n\n".join(parts), info


SITE_PACKAGES = ROOT / ".venv" / "lib" / "python3.12" / "site-packages"
FILLER_PACKAGES = ["sympy", "scipy", "matplotlib", "gradio", "plotly", "rich"]
LONG_LEVELS = {"XL": 240_000, "XXL": 600_000}  # target context tokens (chars / 4 estimate)


def build_long_context(task: Task, target_tokens: int, depth: float = 0.5) -> tuple[str, dict]:
    """Haystack: the task's relevant files (its L2 set) sit at `depth` inside a large pile of other code.
    Filler order: the rest of the task's own repo slice, then Python files from unrelated installed libraries (shuffled with a fixed seed)."""
    import random

    repo = REPOS_DIR / task.meta["repo"]
    relevant = []
    for pattern in task.meta["context"]["L2"]:
        relevant += [f for f in sorted(repo.glob(pattern)) if f.is_file()]
    rel_set = set(relevant)
    rel_parts = [f"=== {f.relative_to(repo)} ===\n{f.read_text()}" for f in relevant]
    rel_tokens = sum(approx_tokens(p) for p in rel_parts)
    own = [f for f in sorted(repo.rglob("*")) if f.is_file() and f.suffix in {".py", ".rst", ".md"} and f not in rel_set and ".git" not in f.parts]
    pool = []
    for pkg in FILLER_PACKAGES:
        if pkg == task.meta["repo"]:
            continue
        pool += [f for f in sorted((SITE_PACKAGES / pkg).rglob("*.py")) if "test" not in "/".join(f.parts[-3:]).lower() and f.stat().st_size < 150_000]
    random.Random(task.id).shuffle(pool)
    fill_parts, total = [], 0
    budget = target_tokens - rel_tokens
    for f in own + pool:
        if total >= budget:
            break
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        t = approx_tokens(txt)
        if total + t > budget:
            continue
        label = f.relative_to(repo) if repo in f.parents else f.relative_to(SITE_PACKAGES)
        fill_parts.append(f"=== {label} ===\n{txt}")
        total += t
    cut, acc = 0, 0
    for i, part in enumerate(fill_parts):
        if acc >= depth * total:
            cut = i
            break
        acc += approx_tokens(part)
    else:
        cut = len(fill_parts)
    parts = fill_parts[:cut] + rel_parts + fill_parts[cut:]
    info = {"level": "XL", "files": len(parts), "tokens": total + rel_tokens, "truncated": False, "relevant_files": len(rel_parts), "depth": depth}
    return "\n\n".join(parts), info


def build_prompt(task: Task, level: str, max_ctx: int = 400_000) -> tuple[str, dict]:
    if level in LONG_LEVELS:
        ctx, info = build_long_context(task, LONG_LEVELS[level])
        info["level"] = level
    else:
        ctx, info = build_context(task, level, max_ctx)
    head = f"TASK_ID: {task.id}\n\n{task.spec}\n\n{FORMAT}\n"
    if task.meta.get("fix_of"):
        broken = {f"solution/{f.name}": f.read_text() for f in sorted((task.root / "reference" / "broken").glob("*.py"))}
        head += ("\n## This is a bug fixing variant\nThe implementation below was written for the task above but it contains a bug. "
                 "Find the bug and return the complete corrected files in the required format. Change only what is needed.\n")
        for path, code in broken.items():
            head += f"\nFILE: {path}\n```python\n{code}\n```\n"
        head += "\n## Bug report\n" + (task.root / "bug_report.md").read_text() + "\n"
    if level == "AG":
        head += ("\nThe original repository is available through tools: list_dir, grep, read_file and git_log (read only, paths are relative to the "
                 "repository root). Explore it as needed, using as few calls as you can, then reply with the final files in the format above. "
                 "Do not call tools in the final reply.\n")
    if ctx:
        intro = ("Below is a very large collection of source files. Part of it is the original repository code that is relevant to this task; "
                 "the rest is unrelated.") if level in LONG_LEVELS else "Below is source code from the original repository, for reference."
        head += f"\n{intro}\n\n{ctx}\n"
    return head, info

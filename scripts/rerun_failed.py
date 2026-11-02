"""Rerun grid cells that errored (found in results/grid/*.log). Output: results/run_task/rows.jsonl and results/grid/rerun.log."""
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo2mini.pipeline import run_one  # noqa: E402

cells = []
for f in sorted(glob.glob(str(Path(__file__).resolve().parents[1] / "results" / "grid" / "[ab]_*.log"))):
    for line in open(f):
        if line.startswith('{"task"'):
            r = json.loads(line)
            if r.get("error"):
                cells.append((r["task"], r["model"], r["level"], r["sample"]))
print(len(cells), "cells to rerun", flush=True)
for task, model, level, sample in cells:
    try:
        r = run_one(task, model, level, sample, rounds=2, effort="low", max_tokens=14000, ctx_cap=150000)
        print(json.dumps({k: r.get(k) for k in ("task", "level", "sample", "pass_rate", "success", "revision_rounds")}), flush=True)
    except Exception as e:
        print(json.dumps({"task": task, "level": level, "sample": sample, "error": str(e)[:200]}), flush=True)

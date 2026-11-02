"""Rerun grid cells that errored (e.g. connection errors). Usage: rerun_errors.py <log glob> ...  Output: rows.jsonl and results/grid/rerun_errors.log.
Effort is taken from the model: beam, gpt52 and gpt6astra at low, gpt41 default."""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.pipeline import run_one  # noqa: E402

EFFORT = {"beam": "low", "gpt52": "low", "gpt6astra": "low", "gpt41": None}
done = {(r["task"], r["model"], r["level"], r["sample"]) for r in (json.loads(l) for l in open(ROOT / "results/run_task/rows.jsonl"))}
cells = []
for pat in sys.argv[1:]:
    for f in sorted(glob.glob(str(ROOT / pat))):
        for line in open(f):
            if line.startswith('{"task"'):
                r = json.loads(line)
                key = (r["task"], r["model"], r["level"], r["sample"])
                if r.get("error") and key not in done and key not in cells:
                    cells.append(key)
print(len(cells), "cells to rerun", flush=True)
for task, model, level, sample in cells:
    try:
        r = run_one(task, model, level, sample, rounds=2, effort=EFFORT[model], max_tokens=14000, ctx_cap=150000)
        print(json.dumps({"task": task, "model": model, "level": level, "sample": sample, "pass_rate": r["pass_rate"], "success": r["success"]}), flush=True)
    except Exception as e:
        print(json.dumps({"task": task, "model": model, "level": level, "sample": sample, "error": str(e)[:200]}), flush=True)

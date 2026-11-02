"""Run one or many (task, model, level, sample) cells. Output: results/run_task/{rows.jsonl,runs/,summary.json,run.log}."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo2mini.pipeline import RESULTS, run_one  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--task", nargs="+", required=True)
ap.add_argument("--model", nargs="+", default=["mock"])
ap.add_argument("--level", nargs="+", default=["L0"])
ap.add_argument("--samples", type=int, default=1)
ap.add_argument("--rounds", type=int, default=3)
ap.add_argument("--effort", default=None)
ap.add_argument("--max-tokens", type=int, default=16000)
ap.add_argument("--tag", default="")
ap.add_argument("--max-tool-turns", type=int, default=20)
ap.add_argument("--ctx-cap", type=int, default=150000)
ap.add_argument("--no-trackio", action="store_true")
a = ap.parse_args()

RESULTS.mkdir(parents=True, exist_ok=True)
rows, t0 = [], time.time()
for task in a.task:
    for model in a.model:
        for level in a.level:
            for s in range(a.samples):
                try:
                    r = run_one(task, model, level, s, a.rounds, a.effort, a.max_tokens, ctx_cap=a.ctx_cap, log_trackio=not a.no_trackio, max_tool_turns=a.max_tool_turns)
                except Exception as e:  # keep the grid going, record the failure
                    r = dict(task=task, model=model, level=level, sample=s, error=str(e)[:500])
                rows.append(r)
                print(json.dumps({k: r.get(k) for k in ("task", "model", "level", "sample", "pass_rate", "success", "revision_rounds", "error")}), flush=True)
summary = dict(n=len(rows), errors=sum("error" in r for r in rows), successes=sum(bool(r.get("success")) for r in rows),
               wall_s=round(time.time() - t0, 1), params=vars(a))
(RESULTS / f"summary{'_' + a.tag if a.tag else ''}.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary))

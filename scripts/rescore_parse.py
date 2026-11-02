"""Rescore runs whose final submission was empty because of a format parse failure, from the saved responses.
Output: results/rescore/parse/{changes.jsonl,rows_before.jsonl}; updates rows.jsonl and result.json of the affected runs."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.sandbox import run_tests  # noqa: E402
from repo2mini.tasks import load_task, parse_files  # noqa: E402

out = ROOT / "results/rescore/parse"
out.mkdir(parents=True, exist_ok=True)
rows_f = ROOT / "results/run_task/rows.jsonl"
shutil.copy(rows_f, out / "rows_before.jsonl")
rows = [json.loads(l) for l in rows_f.read_text().splitlines() if l.strip()]
changes = []
for r in rows:
    d = ROOT / "results/run_task/runs" / r["run_id"]
    msgs = [json.loads(l) for l in (d / "messages.jsonl").read_text().splitlines() if l.strip()]
    if any(m["n_files"] > 0 for m in msgs):
        continue  # a submission existed, already scored
    files = parse_files(msgs[-1]["response"])
    if not files:
        continue
    task = load_task(r["task"])
    rep = run_tests(files, [task.root / "public_tests", task.root / "hidden_tests"])
    new = dict(hidden_passed=rep.passed, hidden_total=rep.total, pass_rate=round(rep.passed / rep.total, 4) if rep.total else 0.0,
               success=rep.all_passed, by_category=rep.by_category, rescored_parse=True)
    changes.append({"run_id": r["run_id"], "model": r["model"], "task": r["task"], "level": r["level"],
                    "before": {"pass_rate": r["pass_rate"], "success": r["success"]}, "after": {"pass_rate": new["pass_rate"], "success": new["success"]}})
    r.update(new)
    (d / "solution").mkdir(exist_ok=True)
    for p, code in files.items():
        (d / p).write_text(code)
    res = json.loads((d / "result.json").read_text())
    res.update(new)
    res["cases"] = [{"name": c["name"], "category": c["category"], "passed": c["passed"]} for c in rep.cases]
    res.pop("final_output", None)
    (d / "result.json").write_text(json.dumps(res, indent=2))
rows_f.write_text("".join(json.dumps(r) + "\n" for r in rows))
(out / "changes.jsonl").write_text("".join(json.dumps(c) + "\n" for c in changes))
print(json.dumps({"rescored": len(changes), "by_model": {m: sum(c["model"] == m for c in changes) for m in sorted({c["model"] for c in changes})}}))

"""Rescore saved solutions of one task against the current hidden tests. Usage: rescore.py <task>.
Output: results/rescore/<task>/{rows_before.jsonl,changes.jsonl}; updates results/run_task/rows.jsonl and each result.json."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.sandbox import run_tests  # noqa: E402
from repo2mini.tasks import load_task  # noqa: E402

task_id = sys.argv[1]
task = load_task(task_id)
rows_f = ROOT / "results/run_task/rows.jsonl"
out = ROOT / "results/rescore" / task_id
out.mkdir(parents=True, exist_ok=True)
shutil.copy(rows_f, out / "rows_before.jsonl")
rows = [json.loads(l) for l in rows_f.read_text().splitlines() if l.strip()]
changes = []
for r in rows:
    if r["task"] != task_id:
        continue
    d = ROOT / "results/run_task/runs" / r["run_id"]
    files = {f"solution/{p.name}": p.read_text() for p in (d / "solution").glob("*.py")}
    rep = run_tests(files, [task.root / "public_tests", task.root / "hidden_tests"])
    new = dict(hidden_passed=rep.passed, hidden_total=rep.total, pass_rate=round(rep.passed / rep.total, 4) if rep.total else 0.0,
               success=rep.all_passed, by_category=rep.by_category)
    changes.append({"run_id": r["run_id"], "before": {k: r[k] for k in new}, "after": new})
    r.update(new)
    res = json.loads((d / "result.json").read_text())
    res.update(new)
    res["cases"] = [{"name": c["name"], "category": c["category"], "passed": c["passed"]} for c in rep.cases]
    (d / "result.json").write_text(json.dumps(res, indent=2))
rows_f.write_text("".join(json.dumps(r) + "\n" for r in rows))
(out / "changes.jsonl").write_text("".join(json.dumps(c) + "\n" for c in changes))
print(json.dumps({"task": task_id, "rescored": len(changes), "success_before": sum(c["before"]["success"] for c in changes),
                  "success_after": sum(c["after"]["success"] for c in changes)}))

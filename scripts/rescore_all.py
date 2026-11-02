"""Rescore every saved run from its stored solution with the current hidden tests and the AST integrity check.
Output: results/rescore/all/{rows_before.jsonl,changes.jsonl,summary.json}; updates rows.jsonl and each result.json.
Runs are scored in parallel. A run that imports, calls or executes the original library is disqualified (pass_rate 0)."""
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.integrity import check  # noqa: E402
from repo2mini.pipeline import integrity_config  # noqa: E402
from repo2mini.sandbox import run_tests  # noqa: E402
from repo2mini.tasks import load_task  # noqa: E402


def score(r):
    d = ROOT / "results/run_task/runs" / r["run_id"]
    files = {f"solution/{p.name}": p.read_text() for p in (d / "solution").glob("*.py")}
    task = load_task(r["task"])
    rep = run_tests(files, [task.root / "public_tests", task.root / "hidden_tests"])
    viol = check(files, integrity_config(task))
    raw = round(rep.passed / rep.total, 4) if rep.total else 0.0
    new = dict(hidden_passed=rep.passed, hidden_total=rep.total, pass_rate=0.0 if viol else raw, raw_pass_rate=raw,
               success=bool(rep.all_passed and not viol), by_category=rep.by_category, integrity_violations=viol, disqualified=bool(viol))
    return r["run_id"], new, [{"name": c["name"], "category": c["category"], "passed": c["passed"]} for c in rep.cases]


if __name__ == "__main__":
    rows_f = ROOT / "results/run_task/rows.jsonl"
    out = ROOT / "results/rescore/all"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(rows_f, out / "rows_before.jsonl")
    rows = [json.loads(l) for l in rows_f.read_text().splitlines() if l.strip()]
    todo = [r for r in rows if r["task"] != "mini_autograd" and (ROOT / "results/run_task/runs" / r["run_id"] / "solution").exists()]
    with ProcessPoolExecutor(6) as ex:
        results = list(ex.map(score, todo, chunksize=4))
    by_id = {rid: (new, cases) for rid, new, cases in results}
    changes = []
    for r in rows:
        if r["run_id"] not in by_id:
            continue
        new, cases = by_id[r["run_id"]]
        if abs(r["pass_rate"] - new["pass_rate"]) > 1e-9 or bool(r["success"]) != new["success"]:
            changes.append({"run_id": r["run_id"], "model": r["model"], "task": r["task"], "level": r["level"],
                            "before": {"pass_rate": r["pass_rate"], "success": r["success"]}, "after": {"pass_rate": new["pass_rate"], "success": new["success"]},
                            "violations": new["integrity_violations"]})
        r.update(new)
        f = ROOT / "results/run_task/runs" / r["run_id"] / "result.json"
        res = json.loads(f.read_text())
        res.update(new)
        res["cases"] = cases
        res.pop("final_output", None)
        f.write_text(json.dumps(res, indent=2))
    rows_f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "changes.jsonl").write_text("".join(json.dumps(c) + "\n" for c in changes))
    summary = {"rescored": len(by_id), "changed": len(changes), "disqualified": sum(r.get("disqualified", False) for r in rows),
               "disqualified_by_model": {m: sum(r.get("disqualified", False) for r in rows if r["model"] == m) for m in sorted({r["model"] for r in rows})}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))

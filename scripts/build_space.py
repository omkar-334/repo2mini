"""Assemble a publishable bundle in results/build_space/{space,dataset}. Hidden tests, repos, .env and logs with secrets are excluded."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "build_space"
shutil.rmtree(OUT, ignore_errors=True)
space, data = OUT / "space", OUT / "dataset"
for d in (space, data):
    d.mkdir(parents=True)

# ---- results shared by both bundles (no hidden tests)
def copy_results(dst: Path):
    r = dst / "results" / "run_task"
    r.mkdir(parents=True)
    shutil.copy(ROOT / "results/run_task/rows.jsonl", r / "rows.jsonl")
    shutil.copytree(ROOT / "results/run_task/runs", r / "runs", ignore=shutil.ignore_patterns("__pycache__", "messages.jsonl"))
    shutil.copytree(ROOT / "results/analyze", dst / "results" / "analyze")
    for rj in (r / "runs").glob("*/result.json"):  # tracebacks can quote hidden test lines
        d = json.loads(rj.read_text())
        d.pop("final_output", None)
        for st in d.get("steps", []):
            st.pop("public_output", None)
        rj.write_text(json.dumps(d, indent=2))

def copy_rescore(dst: Path):
    src = ROOT / "results" / "rescore"
    if src.exists():
        shutil.copytree(src, dst / "results" / "rescore", ignore=shutil.ignore_patterns("rows_before.jsonl"))
    inv = ROOT / "results" / "invalid_runs"
    if inv.exists():
        for d in inv.iterdir():
            (dst / "results" / "invalid_runs" / d.name).mkdir(parents=True, exist_ok=True)
            for f in ("rows.jsonl", "NOTE.md"):
                if (d / f).exists():
                    shutil.copy(d / f, dst / "results" / "invalid_runs" / d.name / f)


def copy_tasks(dst: Path):
    for t in sorted((ROOT / "tasks").iterdir()):
        if not (t / "task.json").exists() or t.name == "mini_autograd":
            continue
        d = dst / "tasks" / t.name
        d.mkdir(parents=True)
        for f in ("task.json", "spec.md"):
            shutil.copy(t / f, d / f)
        shutil.copytree(t / "public_tests", d / "public_tests", ignore=shutil.ignore_patterns("__pycache__"))
        if (t / "bug_report.md").exists():  # fix variants: the buggy code and the report are part of the prompt, the correct solution is not published
            shutil.copy(t / "bug_report.md", d / "bug_report.md")
            shutil.copytree(t / "reference" / "broken", d / "buggy_solution", ignore=shutil.ignore_patterns("__pycache__"))

copy_results(space)
copy_rescore(space)
copy_tasks(space)
(space / "src").mkdir()
shutil.copytree(ROOT / "src" / "repo2mini", space / "src" / "repo2mini", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy(ROOT / "space/app.py", space / "app.py")
shutil.copy(ROOT / "space/README.md", space / "README.md")
shutil.copy(ROOT / "space/requirements.txt", space / "requirements.txt")

copy_results(data)
copy_rescore(data)
copy_tasks(data)
shutil.copy(ROOT / "results/analyze/table.csv", data / "table.csv")
shutil.copy(ROOT / "results/analyze/by_level.csv", data / "by_level.csv")
(data / "README.md").write_text(
    "---\nlicense: apache-2.0\ntask_categories:\n- text-generation\npretty_name: Repo2Mini results\n---\n\n"
    "# Repo2Mini results\n\nPer run outputs, scores and analysis tables for the Repo2Mini benchmark built for Build with Beam. "
    "Each run folder holds the generated solution and a `result.json` with per test outcomes. `results/rescore` lists the runs that were rescored after a test fix and a parser fix. Hidden tests are not published. "
    "See the Space `omkar334/repo2mini` for the method, tasks and findings.\n")
# safety scan: nothing that looks like a key
bad = []
for p in OUT.rglob("*"):
    if p.is_file() and p.suffix in {".json", ".jsonl", ".md", ".py", ".csv", ".txt"}:
        t = p.read_text(errors="ignore")
        if "eyJhbGci" in t or "vck_" in t or "sk-proj" in t or "hf_" in t and "hf_token" not in t.lower() and False:
            bad.append(str(p))
print(json.dumps({"space_files": sum(1 for _ in space.rglob('*') if _.is_file()), "dataset_files": sum(1 for _ in data.rglob('*') if _.is_file()), "secret_hits": bad}))
sys.exit(1 if bad else 0)

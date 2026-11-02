"""Create bug fix tasks by injecting one bug into a reference solution. Output: tasks/<parent>__fixN/ and results/make_fix_tasks/report.json.
A bug is kept only if the hidden tests of the parent task fail on it and the public tests of the parent pass or fail on it as recorded."""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.sandbox import run_tests  # noqa: E402
from repo2mini.tasks import load_task  # noqa: E402

# parent task -> list of (file, old text, new text, one line description of the symptom for humans)
BUGS = {
    "gpt2_forward": [
        ("mini_gpt2.py", "scores = q @ k.transpose(-1, -2) / math.sqrt(self.head_dim)", "scores = q @ k.transpose(-1, -2) / math.sqrt(self.embed_dim)"),
        ("mini_gpt2.py", "(x + 0.044715 * torch.pow(x, 3.0))", "(x + 0.044715 * torch.pow(x, 2.0))"),
    ],
    "gpt2_generate": [
        ("mini_gpt2.py", "pos = torch.arange(past_len, past_len + input_ids.size(1), device=input_ids.device)", "pos = torch.arange(0, input_ids.size(1), device=input_ids.device)"),
        ("mini_gpt2.py", "done = done | (nxt == eos_token_id)", "done = done"),
    ],
    "sortedlist_core": [
        ("mini_sortedlist.py", "if len(self._lists[pos]) > (load << 1):", "if len(self._lists[pos]) > load:"),
        ("mini_sortedlist.py", "return self._bk_right(self._kv(value))", "return self._bk_left(self._kv(value))"),
    ],
    "sortedlist_key": [
        ("mini_sortedlist.py", "stop = self._len if max_key is None else (self._bk_right if max_inc else self._bk_left)(max_key)", "stop = self._len if max_key is None else (self._bk_left if max_inc else self._bk_right)(max_key)"),
        ("mini_sortedlist.py", "values = sorted(chain(chain.from_iterable(self._lists), values), key=self._key_fn)", "values = sorted(chain(values, chain.from_iterable(self._lists)), key=self._key_fn)"),
    ],
    "numpy_quantile": [
        ("mini_quantile.py", "lambda g, _: np.where(g == 0, 0.0, 0.5)),", "lambda g, _: 0.5),"),
        ("mini_quantile.py", '"hazen": (_virtual(0.5, 0.5), lambda g, _: g),', '"hazen": (_virtual(0.5, 0.0), lambda g, _: g),'),
    ],
    "pandas_cut": [
        ("mini_cut.py", 'side = "left" if right else "right"', 'side = "right" if right else "left"'),
        ("mini_cut.py", "    if right:\n        bins[0] -= adj\n    else:\n        bins[-1] += adj", "    if right:\n        bins[-1] += adj\n    else:\n        bins[0] -= adj"),
    ],
    "sort_tracker": [
        ("mini_sort.py", "max(1, math.ceil(frame_rate / 30.0 * lost_track_buffer))", "int(frame_rate / 30.0 * lost_track_buffer)"),
        ("mini_sort.py", "            if t.number_of_successful_updates >= self.minimum_consecutive_frames:\n                if t.tracker_id == -1:", "            if t.number_of_successful_updates > self.minimum_consecutive_frames:\n                if t.tracker_id == -1:"),
    ],
}


def bug_report(parent, rep):
    """Describe the symptom from the first failing hidden test: its name and the assertion values, without the test source."""
    fails = [c for c in rep.cases if not c["passed"]]
    names = [f["name"].split("::")[-1] for f in fails][:4]
    e_lines = [l[1:].strip() for l in rep.output.splitlines() if l.startswith("E ")][:6]
    txt = ("Running the reference checks against this implementation fails.\n\nFailing checks: " + ", ".join(names) +
           f" ({len(fails)} failing in total).\n")
    if e_lines:
        txt += "\nFirst assertion messages:\n" + "\n".join(f"    {l[:200]}" for l in e_lines) + "\n"
    return txt


report = []
for parent, bugs in BUGS.items():
    pt = load_task(parent)
    ref_dir = pt.root / "reference" / "solution"
    for k, (fname, old, new) in enumerate(bugs, start=1):
        src = (ref_dir / fname).read_text()
        assert src.count(old) == 1, (parent, k, "pattern not found exactly once")
        buggy = src.replace(old, new)
        tid = f"{parent}__fix{k}"
        d = ROOT / "tasks" / tid
        shutil.rmtree(d, ignore_errors=True)
        (d / "reference" / "solution").mkdir(parents=True)
        (d / "reference" / "broken").mkdir(parents=True)
        for p in ref_dir.glob("*.py"):
            shutil.copy(p, d / "reference" / "solution" / p.name)
            shutil.copy(p, d / "reference" / "broken" / p.name)
        (d / "reference" / "broken" / fname).write_text(buggy)
        (d / "public_tests").symlink_to(Path("..") / parent / "public_tests")
        (d / "hidden_tests").symlink_to(Path("..") / parent / "hidden_tests")
        shutil.copy(pt.root / "spec.md", d / "spec.md")
        meta = dict(pt.meta, id=tid, fix_of=parent, bug=k, title=f"Fix a bug in {pt.meta['title']}")
        (d / "task.json").write_text(json.dumps(meta, indent=1))
        files = {f"solution/{p.name}": p.read_text() for p in (d / "reference" / "broken").glob("*.py")}
        rep = run_tests(files, [pt.root / "public_tests", pt.root / "hidden_tests"])
        pub = run_tests(files, [pt.root / "public_tests"])
        (d / "bug_report.md").write_text(bug_report(parent, rep))
        report.append(dict(task=tid, hidden_failed=rep.total - rep.passed, hidden_total=rep.total, caught=rep.total > rep.passed, public_passes=pub.all_passed))
        print(json.dumps(report[-1]))
out = ROOT / "results" / "make_fix_tasks"
out.mkdir(parents=True, exist_ok=True)
(out / "report.json").write_text(json.dumps(report, indent=2))
sys.exit(0 if all(r["caught"] for r in report) else 1)

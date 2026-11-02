"""Harness checks: reference passes, broken fails, sandbox hides secrets and enforces timeout, tools are jailed."""
import os
from pathlib import Path

import pytest

from repo2mini.pipeline import run_one
from repo2mini.sandbox import run_tests
from repo2mini.tasks import list_tasks, load_task, parse_files
from repo2mini.tools import RepoTools

ROOT = Path(__file__).resolve().parents[1]


def _files(task, folder):
    return {f"solution/{f.name}": f.read_text() for f in (task.root / "reference" / folder).glob("*.py")}


@pytest.mark.parametrize("tid", list_tasks())
def test_reference_passes_all(tid):
    t = load_task(tid)
    rep = run_tests(_files(t, "solution"), [t.root / "public_tests", t.root / "hidden_tests"])
    assert rep.all_passed, rep.output


@pytest.mark.parametrize("tid", [t for t in list_tasks() if (ROOT / "tasks" / t / "reference" / "broken").exists()])
def test_broken_fails_hidden(tid):
    t = load_task(tid)
    rep = run_tests(_files(t, "broken"), [t.root / "public_tests", t.root / "hidden_tests"])
    assert not rep.all_passed


def test_sandbox_scrubs_env_and_blocks_path_escape(tmp_path):
    os.environ["REFLECTION_API_KEY"] = "secret"
    d = tmp_path / "t"
    d.mkdir()
    (d / "test_api_env.py").write_text("import os\ndef test_x():\n    assert 'REFLECTION_API_KEY' not in os.environ\n")
    rep = run_tests({"../escape.py": "x=1"}, [d])
    assert rep.all_passed and not (tmp_path / "escape.py").exists()


def test_sandbox_timeout(tmp_path):
    d = tmp_path / "t"
    d.mkdir()
    (d / "test_behavior_hang.py").write_text("import time\ndef test_x():\n    time.sleep(30)\n")
    assert run_tests({}, [d], timeout=3).timed_out


def test_parse_files_rejects_traversal():
    txt = "FILE: solution/../evil.py\n```python\nx\n```\nFILE: solution/ok.py\n```python\ny\n```"
    assert list(parse_files(txt)) == ["solution/ok.py"]


def test_parse_files_accepts_missing_opening_fence_and_bold_header():
    txt = "**FILE: solution/a.py**\nx = 1\ny = 2\n```\nsome prose\nFILE: solution/b.py\n```python\nz = 3\n```\n"
    assert parse_files(txt) == {"solution/a.py": "x = 1\ny = 2\n", "solution/b.py": "z = 3\n"}


def test_repo_tools_jail(tmp_path):
    (tmp_path / "a.py").write_text("hello\nworld\n")
    t = RepoTools(tmp_path)
    assert "hello" in t.call("grep", {"pattern": "hello"})
    assert "escapes" in t.call("read_file", {"path": "../../etc/passwd"})


def test_mock_pipeline_end_to_end(tmp_path):
    out = run_one("mini_autograd", "mock", rounds=2, log_trackio=False, results_dir=tmp_path)
    assert out["success"] and out["revision_rounds"] == 1  # broken first, fixed after feedback
    assert (tmp_path / "rows.jsonl").exists()


def test_agentic_level_uses_tools_with_scripted_client(tmp_path, monkeypatch):
    """AG level: the model lists the repo, reads a file, then answers. Tool results must reach the model and be counted."""
    import json as _json

    from repo2mini import pipeline
    from repo2mini.providers import ChatResult

    seen = []

    class Scripted:
        def __init__(self, alias):
            self.n = 0

        def chat(self, messages, **kw):
            seen.append((len(messages), kw.get("tools") is not None))
            self.n += 1
            if self.n == 1:
                call = {"id": "c1", "name": "list_dir", "arguments": _json.dumps({"path": "."})}
                return ChatResult(text="", prompt_tokens=10, completion_tokens=5, tool_calls=[call],
                                  message={"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function",
                                           "function": {"name": "list_dir", "arguments": call["arguments"]}}]})
            t = pipeline.load_task("sortedlist_core")
            body = "".join(f"FILE: solution/{f.name}\n```python\n{f.read_text()}\n```\n" for f in (t.root / "reference" / "solution").glob("*.py"))
            return ChatResult(text=body, prompt_tokens=20, completion_tokens=7)

    monkeypatch.setattr(pipeline, "Client", Scripted)
    out = pipeline.run_one("sortedlist_core", "mock", "AG", rounds=0, log_trackio=False, results_dir=tmp_path)
    assert out["tool_calls"] == 1 and out["success"] and out["prompt_tokens"] == 30
    assert seen[0][1] is True and seen[1][0] == 3  # second request carries user, assistant tool call and tool result


def test_integrity_ignores_mentions_and_flags_real_use():
    from repo2mini.integrity import check

    cfg = {"banned_imports": ["sortedcontainers"], "banned_calls": ["numpy.quantile"]}
    ok = '"""Mini re-implementation of sortedcontainers.SortedList and np.quantile."""\nimport numpy as np\n# np.quantile is not used\nx = "np.quantile"\n'
    assert check({"a.py": ok}, cfg) == []
    assert check({"a.py": "import sortedcontainers"}, cfg)
    assert check({"a.py": "from sortedcontainers.sortedlist import SortedList"}, cfg)
    assert check({"a.py": "import numpy as np\ny = np.quantile([1], .5)"}, cfg)
    assert check({"a.py": "exec(open('x').read())"}, cfg)
    assert check({"a.py": "import importlib"}, cfg)

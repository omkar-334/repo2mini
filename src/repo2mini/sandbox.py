"""Run untrusted generated code and tests in a throwaway directory.

Isolation: fresh temp dir, scrubbed environment (no API keys), `python -I`, CPU and file size limits, wall timeout.
Network is not blocked at the OS level on macOS, so the scrubbed env and timeout are the main guards.
"""
from __future__ import annotations

import os
import resource
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

CONFTEST = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "solution"))
'''


@dataclass
class TestReport:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    timed_out: bool = False
    by_category: dict = field(default_factory=dict)  # category -> [passed, total]
    output: str = ""
    cases: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.failed == 0 and self.errors == 0 and not self.timed_out


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50_000_000, 50_000_000))


def _category(name: str) -> str:
    for c in ("parity", "behavior", "api"):
        if name.startswith(f"test_{c}"):
            return c
    return "other"


def run_tests(files: dict[str, str], test_dirs: list[Path], timeout: int = 90, keep: Path | None = None) -> TestReport:
    work = Path(tempfile.mkdtemp(prefix="r2m_"))
    try:
        (work / "conftest.py").write_text(CONFTEST)
        for rel, code in files.items():
            dest = (work / rel).resolve()
            if work.resolve() not in dest.parents:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(code)
        (work / "solution").mkdir(exist_ok=True)
        for i, d in enumerate(test_dirs):
            shutil.copytree(d, work / f"tests_{i}")
        xml = work / "report.xml"
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work), "LANG": "C.UTF-8"}
        cmd = [sys.executable, "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", "--tb=short",
               str(work)]
        rep = TestReport()
        try:
            p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout, preexec_fn=_limits)
            rep.output = (p.stdout + p.stderr)[-6000:]
        except subprocess.TimeoutExpired as e:
            rep.timed_out = True
            rep.output = ((e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""))[-3000:] + "\nTIMEOUT"
        if xml.exists():
            for tc in ET.parse(xml).getroot().iter("testcase"):
                name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
                cat = _category(tc.get("classname", "").split(".")[-1])
                ok = not any(c.tag in ("failure", "error") for c in tc)
                err = any(c.tag == "error" for c in tc)
                rep.passed += ok
                rep.failed += (not ok) and (not err)
                rep.errors += err
                pc = rep.by_category.setdefault(cat, [0, 0])
                pc[0] += ok
                pc[1] += 1
                rep.cases.append({"name": name, "category": cat, "passed": ok})
        elif not rep.timed_out:
            rep.errors += 1  # collection crash: nothing parsed
        if keep:
            shutil.copytree(work / "solution", keep / "solution", dirs_exist_ok=True)
        return rep
    finally:
        shutil.rmtree(work, ignore_errors=True)

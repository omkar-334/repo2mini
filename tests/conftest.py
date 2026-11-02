"""The hidden tests and reference solutions are not published, so tests that need them are skipped in a public checkout."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = not any((ROOT / "tasks").glob("*/hidden_tests"))


def pytest_collection_modifyitems(config, items):
    if not PRIVATE:
        return
    skip = pytest.mark.skip(reason="hidden tests and reference solutions are withheld")
    for item in items:
        item.add_marker(skip)

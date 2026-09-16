from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_real_csv_exports_are_ignored_but_fixtures_remain_allowed():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "*.csv" in gitignore
    assert "!tests/fixtures/**/*.csv" in gitignore

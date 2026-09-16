"""Source identity and whole-module mutation tests for watch IO projections."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
    Path(__file__).resolve().parents[2] / ".source-checkouts"))
VENDOR = ROOT / "trading_system/tree_replay/_vendor"


def api():
    name = "trading_system.tree_spec.watch_io_source"
    assert importlib.util.find_spec(name) is not None, "watch IO auditor missing"
    return importlib.import_module(name)


def test_actual_pins_logger_sessions_and_inherited_tables_verify():
    r = api().audit_watch_io_source(SOURCE)
    assert r["source_subset_verified"] and r["blockers"] == []
    assert r["checked_projections"] == ["watch._log", "sessions.session_mask",
                                        "sessions.current_session", "map_sessions_dependency"]
    assert not r["ready_for_replay"] and not r["ready_for_training"]


@pytest.mark.parametrize("file,old,new", [
    ("watch_io.py", "import json", "import json\nimport os"),
    ("watch_io.py", 'row.setdefault("sessions", sorted(self.source.current_session()))',
     'row.setdefault("sessions", [])'),
    ("watch_io.py", 'row.setdefault("sessions", sorted(self.source.current_session()))\n        self.source.ensure_out()',
     'self.source.ensure_out()\n        row.setdefault("sessions", sorted(self.source.current_session()))'),
    ("watch_io.py", "self.source.now_epoch()", "0.0"),
    ("watch_io.py", "ensure_ascii=False", "ensure_ascii=False, sort_keys=True"),
    ("watch_sessions.py", "pd.Timestamp(decision_time)", 'pd.Timestamp.now(tz="UTC")'),
    ("watch_sessions.py", "minutes < end", "minutes <= end"),
    ("watch_sessions.py", "if not include_weekends:", "if False:"),
    ("map_sessions.py", '"09:30", "16:00"', '"09:31", "16:00"'),
])
def test_changed_order_clock_boundaries_or_extra_code_block(monkeypatch, file, old, new):
    target = VENDOR / file
    original_read = Path.read_text
    original = original_read(target, encoding="utf-8")
    assert old in original
    def read(path, *args, **kw):
        return original.replace(old, new) if path.resolve() == target.resolve() else original_read(path, *args, **kw)
    monkeypatch.setattr(Path, "read_text", read)
    r = api().audit_watch_io_source(SOURCE)
    assert not r["source_subset_verified"]
    assert f"VENDOR_AST_MISMATCH:{file}" in r["blockers"]


def test_wrong_commit_is_blocked(monkeypatch):
    module = api()
    original_git = module._git
    monkeypatch.setattr(module, "_git", lambda path, *args:
        "0"*40 if args == ("HEAD",) else original_git(path, *args))
    assert "SOURCE_COMMIT_MISMATCH" in module.audit_watch_io_source(SOURCE)["blockers"]


def test_changed_source_blob_is_blocked(monkeypatch):
    original_read = Path.read_text
    target = SOURCE / "chart-desk/scripts/market_watch.py"
    def read(path, *args, **kw):
        content = original_read(path, *args, **kw)
        return content+"\n# source drift\n" if path.resolve() == target.resolve() else content
    monkeypatch.setattr(Path, "read_text", read)
    r = api().audit_watch_io_source(SOURCE)
    assert "SOURCE_BLOB_MISMATCH:scripts/market_watch.py" in r["blockers"]


def test_cli_success_and_missing_source_failure(tmp_path):
    api()
    cmd = [sys.executable, str(ROOT / "tools/check_watch_io_source_parity.py"), "--source-root"]
    for path, code in [(SOURCE, 0), (tmp_path, 2)]:
        result = subprocess.run(cmd+[str(path)], cwd=tmp_path, text=True,
                                capture_output=True, encoding="utf-8", timeout=30)
        assert result.returncode == code, result.stderr
        report = json.loads(result.stdout)
        assert report["source_subset_verified"] is (code == 0)
        assert not report["ready_for_training"]

"""Independent source-identity and complete-projection mutation checks."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
    Path(__file__).resolve().parents[2] / ".source-checkouts"))
RUNTIME = REPO / "trading_system/tree_replay/_vendor/tracker_storage.py"


def api():
    name = "trading_system.tree_spec.tracker_storage_source"
    assert importlib.util.find_spec(name) is not None, "storage source auditor missing"
    return importlib.import_module(name)


def test_actual_pinned_source_and_whole_projection_verify():
    r = api().audit_tracker_storage_source(SOURCE)
    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
    assert r["blockers"] == []
    assert not r["ready_for_replay"] and not r["ready_for_training"]
    assert r["checked_projections"] == ["tracker._load", "tracker._save"]


@pytest.mark.parametrize("old,new", [
    ("len(cur) >= 4", "len(cur) >= 5"),
    ("len(lost) > len(cur) // 2", "len(lost) >= len(cur) // 2"),
    ("cur = json.loads(self.source.read_text())", "cur = {}"),
    ("self.source.audit_creation(cur, d)", "pass"),
    ("if self.source.is_live_test_target():", "if False:"),
    ("ensure_ascii=False, indent=1", "ensure_ascii=False, indent=1, sort_keys=True"),
    ("self.source = source", "self.source = None"),
    ("import json", "import json\nimport os"),
])
def test_changed_runtime_logic_or_extra_code_is_not_accepted(monkeypatch, old, new):
    original_read = Path.read_text
    actual = original_read(RUNTIME, encoding="utf-8")
    assert old in actual
    def read(path, *args, **kwargs):
        return actual.replace(old, new) if path.resolve() == RUNTIME.resolve() else original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    r = api().audit_tracker_storage_source(SOURCE)
    assert not r["source_subset_verified"]
    assert "VENDOR_AST_MISMATCH" in r["blockers"]


def test_changed_retained_source_blob_is_blocked(monkeypatch):
    original_read = Path.read_text
    target = SOURCE / "chart-desk/chartdesk/tracker.py"
    def read(path, *args, **kwargs):
        text = original_read(path, *args, **kwargs)
        return text+"\n# different source bytes\n" if path.resolve() == target.resolve() else text
    monkeypatch.setattr(Path, "read_text", read)
    r = api().audit_tracker_storage_source(SOURCE)
    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]


def test_wrong_commit_blocks_even_with_matching_working_tree(monkeypatch):
    module = api()
    original_git = module._git
    monkeypatch.setattr(module, "_git", lambda path, *args:
        "0"*40 if args == ("HEAD",) else original_git(path, *args))
    r = module.audit_tracker_storage_source(SOURCE)
    assert not r["source_subset_verified"] and "SOURCE_COMMIT_MISMATCH" in r["blockers"]


def test_missing_root_and_missing_runtime_are_blocked(tmp_path, monkeypatch):
    module = api()
    assert not module.audit_tracker_storage_source(tmp_path)["source_subset_verified"]
    monkeypatch.setattr(module, "RUNTIME", tmp_path / "absent.py")
    r = module.audit_tracker_storage_source(SOURCE)
    assert not r["source_subset_verified"]
    assert any("VENDOR_UNREADABLE" in b for b in r["blockers"])


def test_cli_reports_scoped_verification_and_blocked_exit(tmp_path):
    api()  # Missing feature fails here, not as a misleading CLI argument failure.
    command = [sys.executable, str(REPO / "tools/check_tracker_storage_source_parity.py"), "--source-root"]
    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
        result = subprocess.run(command+[str(root)], cwd=tmp_path, text=True,
                                capture_output=True, encoding="utf-8", timeout=30)
        assert result.returncode == code, result.stderr
        report = json.loads(result.stdout)
        assert report["status"] == status and not report["ready_for_training"]

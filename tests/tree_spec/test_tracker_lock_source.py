"""Mutations test the auditor, independently of runtime behavioral tests."""
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
RUNTIME = REPO / "trading_system/tree_replay/_vendor/tracker_lock.py"


def api():
    name = "trading_system.tree_spec.tracker_lock_source"
    assert importlib.util.find_spec(name) is not None, "lock source auditor missing"
    return importlib.import_module(name)


def test_complete_pinned_policy_is_verified_without_full_replay_claim():
    r = api().audit_tracker_lock_source(SOURCE)
    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
    assert r["checked_projections"] == ["tracker.lock_constants", "tracker.LockBusy",
                                        "tracker._busy_for", "tracker._locked"]
    assert r["blockers"] == [] and not r["ready_for_replay"] and not r["ready_for_training"]


@pytest.mark.parametrize("old,new", [
    ("LOCK_TIMEOUT_S = 30.0", "LOCK_TIMEOUT_S = 3.0"),
    ("RESOLVE_LOCK_WAIT_S = 3.0", "RESOLVE_LOCK_WAIT_S = 30.0"),
    ("LOCK_STALL_S = 120.0", "LOCK_STALL_S = 121.0"),
    ("stuck < LOCK_STALL_S", "stuck <= LOCK_STALL_S"),
    ('self.held["depth"] > 0', 'self.held["depth"] > 1'),
    ('self.held = {"depth": 0}', 'self.held = {"depth": 1}'),
    ("self.source.now_epoch() - float(self.source.read_busy())", "0.0"),
    ("self.source.clear_busy()", "pass"),
    ("self.source.release(f)", "pass"),
    ("f.close()", "pass"),
    ("@contextmanager", ""),
    ("from contextlib import contextmanager", "from contextlib import contextmanager\nimport os"),
])
def test_changed_policy_or_extra_code_is_blocked(monkeypatch, old, new):
    original = Path.read_text
    text = original(RUNTIME, encoding="utf-8")
    assert old in text
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw:
        text.replace(old, new) if p.resolve() == RUNTIME.resolve() else original(p, *a, **kw))
    r = api().audit_tracker_lock_source(SOURCE)
    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]


def test_wrong_source_commit_and_baseline_cannot_certify_same_code(monkeypatch):
    module = api()
    original_git = module._git
    monkeypatch.setattr(module, "_git", lambda p, *a:
        "0"*40 if a == ("HEAD",) else original_git(p, *a))
    assert "SOURCE_COMMIT_MISMATCH" in module.audit_tracker_lock_source(SOURCE)["blockers"]
    monkeypatch.setattr(module, "_git", original_git)
    original_read = Path.read_text
    def read(path, *a, **kw):
        text = original_read(path, *a, **kw)
        return text.replace(module.COMMIT, "0"*40) if path.name == "existing-alerts-baseline.json" else text
    monkeypatch.setattr(Path, "read_text", read)
    assert "BASELINE_COMMIT_MISMATCH" in module.audit_tracker_lock_source(SOURCE)["blockers"]


def test_changed_source_blob_blocks_even_when_selected_functions_match(monkeypatch):
    original = Path.read_text
    target = SOURCE / "chart-desk/chartdesk/tracker.py"
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw:
        original(p, *a, **kw)+("\n# changed\n" if p.resolve() == target.resolve() else ""))
    assert "SOURCE_BLOB_MISMATCH" in api().audit_tracker_lock_source(SOURCE)["blockers"]


def test_missing_root_and_runtime_report_blocked(tmp_path, monkeypatch):
    module = api()
    assert not module.audit_tracker_lock_source(tmp_path)["source_subset_verified"]
    monkeypatch.setattr(module, "RUNTIME", tmp_path / "missing.py")
    assert any("VENDOR_UNREADABLE" in b for b in module.audit_tracker_lock_source(SOURCE)["blockers"])


def test_cli_outside_repo_emits_json_and_correct_verification_exit(tmp_path):
    api()
    command = [sys.executable, str(REPO / "tools/check_tracker_lock_source_parity.py"), "--source-root"]
    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
        run = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
                             text=True, encoding="utf-8", timeout=30)
        assert run.returncode == code, run.stderr
        r = json.loads(run.stdout)
        assert r["status"] == status and not r["ready_for_replay"] and not r["ready_for_training"]

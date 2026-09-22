"""Independent retained-source proof for the tracker lifecycle caller seam."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
RETAINED = Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts"))


def api():
    name = "trading_system.tree_spec.tracker_lifecycle_caller_source"
    assert importlib.util.find_spec(name) is not None, "tracker lifecycle caller source auditor missing"
    return importlib.import_module(name)


def test_pinned_tracker_caller_seam_and_actual_children_are_verified():
    result = api().audit_tracker_lifecycle_caller_source(RETAINED)
    assert result["status"] == "VERIFIED"
    assert result["source_subset_verified"] and result["blockers"] == []
    assert set(result["dependencies"]) == {"lifecycle_gate_park", "tracker_lock"}
    assert not result["ready_for_replay"] and not result["ready_for_training"]


def test_missing_retained_root_fails_closed_without_readiness(tmp_path):
    result = api().audit_tracker_lifecycle_caller_source(tmp_path / "missing")
    assert result["status"] == "BLOCKED"
    assert result["blockers"] and not result["source_subset_verified"]
    assert not result["ready_for_replay"] and not result["ready_for_training"]


def test_cli_uses_explicit_root_and_only_certifies_verified_reports(tmp_path):
    cli = REPO / "tools/check_tracker_lifecycle_caller_source_parity.py"
    for root, returncode, status in ((RETAINED, 0, "VERIFIED"), (tmp_path / "missing", 2, "BLOCKED")):
        run = subprocess.run(
            [sys.executable, "-B", str(cli), "--source-root", str(root)],
            cwd=tmp_path, text=True, capture_output=True, check=False,
        )
        assert run.returncode == returncode, run.stderr
        report = json.loads(run.stdout)
        assert report["status"] == status
        assert not report["ready_for_replay"] and not report["ready_for_training"]


def test_audit_rejects_changed_only_tail_order_and_live_lockbusy_boundary(tmp_path, monkeypatch):
    module = api()
    source = RETAINED / "chart-desk/chartdesk/tracker.py"
    original = Path.read_text
    text = original(source, encoding="utf-8")
    mutated = text.replace(
        "out = _persist_gated_lifecycle(out, d)\n        _save(d)",
        "_save(d)\n        out = _persist_gated_lifecycle(out, d)", 1,
    ).replace(
        "with _locked(skip_if_busy=True):\n            return _check_live_locked()",
        "with _locked(skip_if_busy=False):\n            return _check_live_locked()",
        1,
    )
    monkeypatch.setattr(
        Path, "read_text",
        lambda path, *args, **kwargs: mutated if path.resolve() == source.resolve() else original(path, *args, **kwargs),
    )
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "SOURCE_TAIL_MISMATCH:check" in result["blockers"]
    assert "SOURCE_WRAPPER_MISMATCH:check_live" in result["blockers"]


def test_audit_rejects_second_changed_only_tail_order(tmp_path, monkeypatch):
    module = api()
    source = RETAINED / "chart-desk/chartdesk/tracker.py"
    original = Path.read_text
    text = original(source, encoding="utf-8")
    tail = "out = _persist_gated_lifecycle(out, d)\n        _save(d)"
    before, separator, after = text.rpartition(tail)
    assert separator and before.count(tail) == 1
    mutated = before + "_save(d)\n        out = _persist_gated_lifecycle(out, d)" + after
    monkeypatch.setattr(
        Path, "read_text",
        lambda path, *args, **kwargs: mutated if path.resolve() == source.resolve() else original(path, *args, **kwargs),
    )
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "SOURCE_TAIL_MISMATCH:_check_live_locked" in result["blockers"]


def test_audit_rejects_tracker_lock_child_audit_identity_drift(monkeypatch):
    module = api()
    monkeypatch.setitem(
        module.CHILD_AUDITS,
        "tracker_lock",
        module.CHILD_AUDITS["lifecycle_gate_park"],
    )
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:tracker_lock" in result["blockers"]


def test_audit_rejects_baseline_commit_and_tracker_blob_pin_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in result["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in result["blockers"]
    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in module.audit_tracker_lifecycle_caller_source(RETAINED)["blockers"]


@pytest.mark.parametrize("old,new", [
    ("self.gate = LifecycleGate(source)", "self.gate = None"),
    ("with self.source.locked(skip_if_busy=True):", "with self.source.locked(skip_if_busy=False):"),
    ("except LockBusy:\n            return []", "except ValueError:\n            return []"),
])
def test_audit_rejects_runtime_constructor_interface_and_lockbusy_drift(tmp_path, monkeypatch, old, new):
    module = api()
    runtime = REPO / "trading_system/tree_replay/lifecycle_caller.py"
    original = Path.read_text
    text = original(runtime, encoding="utf-8")
    assert old in text
    monkeypatch.setattr(
        Path, "read_text",
        lambda path, *args, **kwargs: text.replace(old, new, 1) if path.resolve() == runtime.resolve() else original(path, *args, **kwargs),
    )
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "RUNTIME_AST_MISMATCH:tracker_lifecycle_caller" in result["blockers"]


def test_audit_fails_closed_for_blocked_exceptional_or_malformed_child(monkeypatch):
    module = api()
    original = module._child_audit

    def blocked(name, root):
        if name == "lifecycle_gate_park":
            return {"source_subset_verified": False, "blockers": ["CHILD_BLOCKED"]}
        return original(name, root)

    monkeypatch.setattr(module, "_child_audit", blocked)
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "DEPENDENCY:lifecycle_gate_park:CHILD_BLOCKED" in result["blockers"]
    monkeypatch.undo()

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: (_ for _ in ()).throw(RuntimeError("child unavailable")))
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "DEPENDENCY:lifecycle_gate_park:UNREADABLE:RuntimeError" in result["blockers"]
    monkeypatch.undo()

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"source_subset_verified": "yes", "blockers": []})
    result = module.audit_tracker_lifecycle_caller_source(RETAINED)
    assert "DEPENDENCY:lifecycle_gate_park:UNREADABLE:TypeError" in result["blockers"]

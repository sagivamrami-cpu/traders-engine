from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "trading_system/tree_replay/full_tree_capture.py"


def api():
    name = "trading_system.tree_spec.full_tree_capture_source"
    assert importlib.util.find_spec(name) is not None, "full-tree capture auditor missing"
    return importlib.import_module(name)


def test_capture_source_audit_requires_supplied_only_actual_tree_composition():
    report = api().check_full_tree_capture_source()

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["source_bindings"] == ["TreeReader", "TreeRevalidation"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_capture_source_audit_blocks_a_final_walk_injection(monkeypatch):
    module = api()
    original = CAPTURE.read_text(encoding="utf-8")
    assert "def capture_walk(self)" in original
    changed = original.replace("def capture_walk(self)", "def capture_walk(self, walk)", 1)
    actual_read = Path.read_text

    def read_text(path, *args, **kwargs):
        return changed if path.resolve() == CAPTURE.resolve() else actual_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    report = module.check_full_tree_capture_source()

    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["FINAL_RESULT_INJECTION_SURFACE"]


def test_capture_source_audit_blocks_live_loader_import(monkeypatch):
    module = api()
    original = CAPTURE.read_text(encoding="utf-8")
    actual_read = Path.read_text

    def read_text(path, *args, **kwargs):
        return "import requests\n" + original if path.resolve() == CAPTURE.resolve() else actual_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    report = module.check_full_tree_capture_source()

    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["FORBIDDEN_LIVE_IMPORT:requests"]

from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path


import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get(
    "TR_TREE_SOURCE_ROOT",
    "C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149",
))
PROVIDER = ROOT / "trading_system/tree_replay/full_tree_provider.py"


def api():
    name = "trading_system.tree_spec.full_tree_replay_source"
    assert importlib.util.find_spec(name) is not None, "full-tree replay auditor missing"
    return importlib.import_module(name)


def test_full_tree_provider_audit_requires_actual_source_composition_without_readiness_claims():
    report = api().check_full_tree_replay_source(SOURCE)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert set(report["provider_ports"]) == set(api().REQUIRED_PROVIDER_PORTS)
    assert report["source_bindings"] == ["TreeReader", "TreeRevalidation"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_audit_fails_closed_when_a_required_raw_port_is_removed(monkeypatch):
    module = api()
    original = PROVIDER.read_text(encoding="utf-8")
    assert "def read_tv_csv(" in original
    changed = original.replace("    def read_tv_csv(", "    def removed_tv_csv(", 1)
    actual_read = Path.read_text

    def read_text(path, *args, **kwargs):
        return changed if path.resolve() == PROVIDER.resolve() else actual_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    report = module.check_full_tree_replay_source(SOURCE)

    assert report["status"] == "BLOCKED"
    assert "MISSING_PROVIDER_PORT:read_tv_csv" in report["blockers"]


def test_audit_requires_the_pinned_tree_source_not_just_a_chart_desk_directory(tmp_path):
    (tmp_path / "chart-desk").mkdir()

    report = api().check_full_tree_replay_source(tmp_path)

    assert report["status"] == "BLOCKED"
    assert any(blocker.startswith("SOURCE_TREE:") for blocker in report["blockers"])


def test_audit_fails_closed_when_the_pinned_tree_audit_cannot_be_read(monkeypatch):
    module = api()

    def unavailable(_root):
        raise OSError("retained source unavailable")

    monkeypatch.setattr(module, "audit_tree_walk_source", unavailable)
    report = module.check_full_tree_replay_source(SOURCE)

    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["SOURCE_TREE_UNREADABLE:OSError"]

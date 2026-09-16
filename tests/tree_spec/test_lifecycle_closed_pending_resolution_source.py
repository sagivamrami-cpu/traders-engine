"""Contract tests for the inert closed-bar PENDING retained-source audit."""
from __future__ import annotations

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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_closed_pending_resolution.py"


def api():
    name = "trading_system.tree_spec.lifecycle_closed_pending_resolution_source"
    assert importlib.util.find_spec(name) is not None, "closed PENDING source auditor missing"
    return importlib.import_module(name)


def verified_child_reports(module):
    required = dict(module._REQUIRED_CHILD_PROJECTIONS)
    return {
        name: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": list(required[name]),
            "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False,
            "ready_for_training": False,
        }
        for name in module.CHILD_AUDITS
    }


def test_exact_closed_pending_projection_and_children_verify():
    report = api().audit_lifecycle_closed_pending_resolution_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_closed_pending_resolution"]
    assert tuple(report["dependencies"]) == (
        "lifecycle_outcome_shelf",
        "lifecycle_transitions",
        "tree_revalidation",
        "lifecycle_primitives",
    )
    assert all(
        child["source_subset_verified"] is True
        and child["ready_for_replay"] is False
        and child["ready_for_training"] is False
        for child in report["dependencies"].values()
    )
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_source_extractor_selects_only_closed_pending_branch_in_source_order():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    fragment = module._extract_closed_pending_fragment(source)

    assert module._fragment_names(fragment) == (
        "expiry",
        "if_touched_entry",
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "(float(now) - float(trade[\"ts\"])) > self.outcomes._expire_h(trade) * 3600 and not touched_entry",
            "(float(now) - float(trade[\"ts\"])) >= self.outcomes._expire_h(trade) * 3600 and not touched_entry",
        ),
        ("ran = (start - float(low)) if short else (float(high) - start)", "ran = (float(high) - start) if short else (start - float(low))"),
        ("self.source.now_epoch()", "float(now)"),
        ("if touched_stop:", "if False:"),
        ("stopped_ambiguous", "wrong_ambiguity"),
        ("if self.outcomes.has_open(trade[\"symbol\"], trade[\"direction\"], state=state):", "if False:"),
        ("self.revalidation.revalidate_pending(trade, now=now)", "(True, \"verified\", True)"),
    ],
)
def test_audit_rejects_expiry_missed_r_clock_touch_conflict_stop_and_fill_drift(
    tmp_path, monkeypatch, old, new
):
    module = api()
    children = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: children[name])
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_closed_pending_resolution.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_closed_pending_resolution_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_closed_pending_resolution" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_source_pin_branch_shape_and_malformed_child_reports_fail_closed(monkeypatch):
    module = api()
    children = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: children[name])
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_closed_pending_resolution_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_closed_pending_resolution_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"status": "VERIFIED"})
    report = module.audit_lifecycle_closed_pending_resolution_source(RETAINED)
    assert "DEPENDENCY:lifecycle_outcome_shelf:UNREADABLE:TypeError" in report["blockers"]

    monkeypatch.undo()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_CLOSED_PENDING_BRANCH_MISSING_OR_AMBIGUOUS"):
        module._extract_closed_pending_fragment(
            source.replace('if t["state"] == "PENDING":', 'if t["state"] == "PENDING_RENAMED":', 1)
        )


def test_cli_requires_explicit_root_and_emits_valid_blocked_json(capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_closed_pending_resolution_source_parity.py"
    spec = importlib.util.spec_from_file_location("closed_pending_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "BLOCKED"
    assert missing["ready_for_replay"] is False
    assert missing["ready_for_training"] is False

    monkeypatch.setattr(
        cli,
        "audit_lifecycle_closed_pending_resolution_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_verifies_from_unrelated_cwd_and_fails_closed_for_missing_root(tmp_path):
    cli = REPO / "tools/check_lifecycle_closed_pending_resolution_source_parity.py"
    good = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["status"] == "VERIFIED"

    bad = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(tmp_path / "missing")],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert bad.returncode == 2
    assert json.loads(bad.stdout)["status"] == "BLOCKED"

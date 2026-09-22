"""Contract tests for the inert PENDING-resolution retained-source audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_pending_resolution.py"


def verified_child_reports(module):
    return {
        name: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": list(dict(module._REQUIRED_CHILD_PROJECTIONS)[name]),
            "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False,
            "ready_for_training": False,
        }
        for name in module.CHILD_AUDITS
    }


def api():
    name = "trading_system.tree_spec.lifecycle_pending_resolution_source"
    assert importlib.util.find_spec(name) is not None, "PENDING resolution source auditor missing"
    return importlib.import_module(name)


def test_exact_pending_branch_projection_and_composed_child_audits_verify():
    report = api().audit_lifecycle_pending_resolution_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_pending_resolution"]
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


def test_source_extractor_selects_only_the_ordered_pending_branch():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    fragment = module._extract_pending_fragment(source)

    assert module._fragment_names(fragment) == (
        "entry_band",
        "extremes",
        "touch",
        "if_not_touched",
        "if_open_slot",
        "revalidate",
        "if_not_revalidated",
        "open_state",
        "revalidation_verified",
        "fill_verification_reason",
        "fill_timestamps",
        "changed",
        "fill_caveat",
        "fill_message",
    )


def test_missing_retained_root_fails_closed_without_readiness(tmp_path):
    report = api().audit_lifecycle_pending_resolution_source(tmp_path / "missing")

    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("high >= zone_low if short else low <= zone_high", "low >= zone_low if short else high <= zone_high"),
        ("self.outcomes.has_open(trade[\"symbol\"], trade[\"direction\"], state=state)", "False"),
        ("self.revalidation.revalidate_pending(trade)", "(False, \"drift\", False)"),
        ("open_slot_conflict_at_fill", "wrong_conflict_result"),
        ("invalidated_at_fill", "wrong_invalidated_result"),
        ("trade[\"filled_ts\"] = trade[\"progress_ts\"] = self.source.now_epoch()", "trade[\"filled_ts\"] = self.source.now_epoch(); trade[\"progress_ts\"] = self.source.now_epoch()"),
        ("self.transitions._fill_line(trade, name, side) + caveat", "self.transitions._fill_line(trade, name, side)"),
        ("from .lifecycle_bars import _entry_band", "from .pricing import entry_zone"),
    ],
)
def test_audit_rejects_touch_path_timestamp_and_dependency_drift(tmp_path, monkeypatch, old, new):
    module = api()
    children = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: children[name])
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_pending_resolution.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_pending_resolution_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_pending_resolution" in report["blockers"]
    assert report["source_subset_verified"] is False


def test_source_pin_and_branch_shape_drift_fail_closed(monkeypatch):
    module = api()
    children = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: children[name])
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_pending_resolution_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_pending_resolution_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "_EXPECTED_FRAGMENT_NAMES", tuple(reversed(module._EXPECTED_FRAGMENT_NAMES)))
    report = module.audit_lifecycle_pending_resolution_source(RETAINED)
    assert any("SOURCE_PENDING_BRANCH_ORDER_MISMATCH" in row for row in report["blockers"])


def test_child_contract_identity_and_malformed_child_reports_fail_closed(monkeypatch):
    module = api()
    with pytest.raises(TypeError):
        module._EXPECTED_CHILD_AUDITS[0] = ("tampered",)

    monkeypatch.setitem(module.CHILD_AUDITS, "tree_revalidation", ("wrong", "wrong"))
    report = module.audit_lifecycle_pending_resolution_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:tree_revalidation" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(
        module,
        "_child_audit",
        lambda _name, _root: {"status": "VERIFIED", "source_subset_verified": True, "blockers": []},
    )
    report = module.audit_lifecycle_pending_resolution_source(RETAINED)
    assert "DEPENDENCY:lifecycle_outcome_shelf:UNREADABLE:TypeError" in report["blockers"]


def test_cli_requires_explicit_root_and_emits_json_for_all_errors(tmp_path, capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_pending_resolution_source_parity.py"
    spec = importlib.util.spec_from_file_location("pending_resolution_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "BLOCKED"
    assert missing["ready_for_replay"] is False
    assert missing["ready_for_training"] is False

    monkeypatch.setattr(cli, "audit_lifecycle_pending_resolution_source", lambda _root: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_survives_a_json_encoder_failure_with_a_valid_blocked_payload(capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_pending_resolution_source_parity.py"
    spec = importlib.util.spec_from_file_location("pending_resolution_parity_cli_json", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_pending_resolution_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("json")))

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_cli_verifies_from_unrelated_cwd_and_fails_closed_for_missing_root(tmp_path):
    cli = REPO / "tools/check_lifecycle_pending_resolution_source_parity.py"
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

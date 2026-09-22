"""Contract tests for the retained-source ordinary OPEN-resolution audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_open_ordinary_resolution.py"


def api():
    name = "trading_system.tree_spec.lifecycle_open_ordinary_resolution_source"
    assert importlib.util.find_spec(name) is not None, "ordinary OPEN source auditor missing"
    return importlib.import_module(name)


def verified_child_reports(module):
    return {
        name: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": list(dict(module._REQUIRED_CHILD_PROJECTIONS)[name]),
            "dependencies": {},
            "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False,
            "ready_for_training": False,
        }
        for name in module.CHILD_AUDITS
    }


def test_complete_ordinary_open_projection_and_accepted_children_verify_without_readiness():
    report = api().audit_lifecycle_open_ordinary_resolution_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_open_ordinary_resolution"]
    assert tuple(report["dependencies"]) == (
        "lifecycle_outcome_shelf",
        "lifecycle_transitions",
    )
    assert report["source_commits"] == {
        "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
    }
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("low: float, high: float", "high: float, low: float"),
        ("self.transitions._protective(trade, short)", 'trade["stop"]'),
        ("low <= target_one if short else high >= target_one", "high <= target_one if short else low >= target_one"),
        ("low <= target_price if short else high >= target_price", "high <= target_price if short else low >= target_price"),
        ("self.transitions._mark_terminal(trade, \"DONE\")", "trade[\"state\"] = \"DONE\""),
        ("self.outcomes._outcome({**trade, \"result\": tag.lower()})", "pass"),
        ("self.transitions._resolve_protective(trade, name, side)", "(\"wrong\", \"wrong\", \"DONE\")"),
    ],
)
def test_audit_rejects_low_high_projection_mutation(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated_vendor = tmp_path / "lifecycle_open_ordinary_resolution.py"
    mutated_vendor.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated_vendor))
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])

    report = module.audit_lifecycle_open_ordinary_resolution_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_open_ordinary_resolution" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_pinned_physical_fragment_requires_its_full_order():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    fragment = module._extract_ordinary_fragment(source)

    assert module._fragment_names(fragment) == (
        "tp1_now", "targets_guard", "tp1_value", "tp1_touch", "progress",
        "progress_guard", "target_loop", "recomputed_protection", "all_targets",
        "protective_guard",
    )
    slice_start = source.rindex("            tp1_now = False")
    changed = source[:slice_start] + source[slice_start:].replace(
        't["progress_ts"] = time.time()', 'changed = True', 1,
    )
    with pytest.raises(ValueError, match="SOURCE_OPEN_ORDINARY_ORDER_MISMATCH"):
        module._extract_ordinary_fragment(changed)


def test_source_commit_blob_missing_root_and_malformed_child_reports_fail_closed(monkeypatch, tmp_path):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_open_ordinary_resolution_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_open_ordinary_resolution_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    report = module.audit_lifecycle_open_ordinary_resolution_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"bad": "report"})
    report = module.audit_lifecycle_open_ordinary_resolution_source(RETAINED)
    assert any(row.startswith("DEPENDENCY:") for row in report["blockers"])


def test_cli_requires_explicit_root_and_emits_valid_blocked_json_on_errors(tmp_path, capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_open_ordinary_resolution_source_parity.py"
    spec = importlib.util.spec_from_file_location("ordinary_open_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "BLOCKED"
    assert missing["ready_for_replay"] is False
    assert missing["ready_for_training"] is False

    monkeypatch.setattr(
        cli,
        "audit_lifecycle_open_ordinary_resolution_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_survives_malformed_audit_and_json_encoder_failures(capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_open_ordinary_resolution_source_parity.py"
    spec = importlib.util.spec_from_file_location("ordinary_open_parity_cli_json", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_open_ordinary_resolution_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": ["contradiction"],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

    monkeypatch.setattr(cli, "audit_lifecycle_open_ordinary_resolution_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(
        cli.json,
        "dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("json")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_cli_verifies_from_unrelated_directory_and_missing_root_fails_closed(tmp_path):
    cli = REPO / "tools/check_lifecycle_open_ordinary_resolution_source_parity.py"
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
    report = json.loads(bad.stdout)
    assert report["status"] == "BLOCKED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

"""Contract tests for the retained-source OPEN minimum-success audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_open_minimum_success.py"


def api():
    name = "trading_system.tree_spec.lifecycle_open_minimum_success_source"
    assert importlib.util.find_spec(name) is not None, "OPEN minimum-success source auditor missing"
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


def test_complete_minimum_success_projection_and_accepted_children_verify_without_readiness():
    report = api().audit_lifecycle_open_minimum_success_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_open_minimum_success"]
    assert tuple(report["dependencies"]) == (
        "lifecycle_open_postfill_evidence",
        "lifecycle_transitions",
        "lifecycle_outcome_shelf",
    )
    assert report["source_commits"] == {
        "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
    }
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("not minimum_message and not hit_protect", "not hit_protect and not minimum_message"),
        ("high >= protective if short else low <= protective",
         "low >= protective if short else high <= protective"),
        ("trade, low if short else high, short", "trade, high if short else low, short"),
        ("minimum(trade[\"symbol\"])", "minimum(\"wrong-symbol\")"),
        ("{**trade, \"result\": \"minimum_success\"}", "trade"),
    ],
)
def test_audit_rejects_quote_protection_progress_and_raw_fact_projection_mutations(
    tmp_path, monkeypatch, old, new
):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_open_minimum_success.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])

    report = module.audit_lifecycle_open_minimum_success_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_open_minimum_success" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_pinned_physical_minimum_branch_requires_quote_progress_and_message_outcome_order():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    branch = module._extract_minimum_success_branch(source)

    assert module._minimum_success_names(branch) == (
        "hit_protect", "quote", "quote_timestamp", "quote_minimum",
        "minimum_guard", "directional_progress", "progress_guard",
        "reported_points", "message_before_outcome", "minimum_outcome", "changed",
    )
    progress_mutant = source.replace(
        'steps = _progress_steps(t, _lo if short else _hi, short)',
        'steps = _progress_steps(t, _hi if short else _lo, short)',
        1,
    )
    with pytest.raises(ValueError, match="SOURCE_OPEN_MINIMUM_SUCCESS_ORDER_MISMATCH"):
        module._extract_minimum_success_branch(progress_mutant)

    ordered = (
        'out.append((minimum_msg, t["to_group"]))\n'
        '                _outcome({**t, "result": "minimum_success"})'
    )
    reversed_order = (
        '_outcome({**t, "result": "minimum_success"})\n'
        '                out.append((minimum_msg, t["to_group"]))'
    )
    assert ordered in source
    slice_offset = sum(
        len(line) for line in source.splitlines(keepends=True)[:module.SOURCE_START_LINE - 1]
    )
    order_mutant = source[:slice_offset] + source[slice_offset:].replace(
        ordered, reversed_order, 1,
    )
    with pytest.raises(ValueError, match="SOURCE_OPEN_MINIMUM_SUCCESS_ORDER_MISMATCH"):
        module._extract_minimum_success_branch(order_mutant)


def test_source_identity_blob_missing_root_and_malformed_children_fail_closed(monkeypatch, tmp_path):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_open_minimum_success_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_open_minimum_success_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    report = module.audit_lifecycle_open_minimum_success_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"bad": "report"})
    report = module.audit_lifecycle_open_minimum_success_source(RETAINED)
    assert any(row.startswith("DEPENDENCY:") for row in report["blockers"])


def test_cli_requires_explicit_root_and_emits_valid_blocked_json_on_errors(capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_open_minimum_success_source_parity.py"
    spec = importlib.util.spec_from_file_location("minimum_success_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "BLOCKED"
    assert missing["ready_for_replay"] is False
    assert missing["ready_for_training"] is False

    monkeypatch.setattr(
        cli,
        "audit_lifecycle_open_minimum_success_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


@pytest.mark.parametrize(
    "result",
    [
        "not a report",
        {"status": "VERIFIED", "source_subset_verified": True, "blockers": ["CONTRADICTION"]},
        {"status": "BLOCKED", "source_subset_verified": False, "blockers": []},
        {"status": "VERIFIED", "source_subset_verified": True, "blockers": [], "bad": object()},
    ],
)
def test_cli_turns_malformed_contradictory_and_unserializable_audits_into_blocked_json(
    monkeypatch, capsys, result
):
    cli_path = REPO / "tools/check_lifecycle_open_minimum_success_source_parity.py"
    spec = importlib.util.spec_from_file_location("minimum_success_parity_cli_json", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_open_minimum_success_source", lambda _root: result)

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_cli_verifies_from_unrelated_directory_and_missing_root_fails_closed(tmp_path):
    cli = REPO / "tools/check_lifecycle_open_minimum_success_source_parity.py"
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

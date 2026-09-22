"""Contract tests for the retained-source OPEN protection audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_open_protection.py"


def api():
    name = "trading_system.tree_spec.lifecycle_open_protection_source"
    assert importlib.util.find_spec(name) is not None, "OPEN protection source auditor missing"
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


def test_complete_open_protection_projection_and_accepted_children_verify_without_readiness():
    report = api().audit_lifecycle_open_protection_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_open_protection"]
    assert set(report["dependencies"]) == {
        "lifecycle_outcome_shelf", "lifecycle_transitions",
    }
    assert report["source_commits"] == {
        "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
    }
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('from .lifecycle_outcome_shelf import LifecycleOutcomeShelf',
         'from .lifecycle_outcome_shelf import NotTheOutcomeShelf'),
        ('trade["direction"] == "שורט"', 'trade["direction"] == "לונג"'),
        ("self.transitions._protective(trade, short)", "trade[\"stop\"]"),
        ("trade, low, high, short, protective", "trade, high, low, short, protective"),
        ('"STOPPED" if not trade["hit"] else "DONE"',
         '"DONE" if not trade["hit"] else "STOPPED"'),
        ('{**trade, "result": result}', "trade"),
        ("[(message, trade[\"to_group\"])], True", "[(message, True)], True"),
    ],
)
def test_audit_rejects_runtime_projection_and_dependency_drift(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_open_protection.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])

    report = module.audit_lifecycle_open_protection_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_open_protection" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_source_extraction_parses_only_the_pinned_protection_slice_and_requires_its_order():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    branch = module._extract_protection_branch(source)

    assert module._protection_names(branch) == (
        "hit_protect", "quote", "quote_timestamp", "quote_minimum",
        "minimum_success", "ambiguity",
    )
    changed = source.replace("if _ambiguous_touch(t, _lo, _hi, short, protective):", "if True:", 1)
    with pytest.raises(ValueError, match="SOURCE_OPEN_PROTECTION_ORDER_MISMATCH"):
        module._extract_protection_branch(changed)


def test_audit_rejects_authority_blob_missing_source_projection_and_child_failures(monkeypatch, tmp_path):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_open_protection_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_open_protection_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    report = module.audit_lifecycle_open_protection_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False

    monkeypatch.setattr(
        module, "_projection", lambda _text: (_ for _ in ()).throw(RuntimeError("bad audit"))
    )
    report = module.audit_lifecycle_open_protection_source(RETAINED)
    assert any(
        row.startswith("SOURCE_PROJECTION_UNREADABLE:lifecycle_open_protection:RuntimeError")
        for row in report["blockers"]
    )

    monkeypatch.undo()
    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"bad": "report"})
    report = module.audit_lifecycle_open_protection_source(RETAINED)
    assert any(row.startswith("DEPENDENCY:") for row in report["blockers"])


def test_explicit_root_cli_verifies_from_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_open_protection_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_cli_fails_closed_as_json_for_missing_explicit_root(tmp_path):
    cli = REPO / "tools/check_lifecycle_open_protection_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(tmp_path / "missing")],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert run.returncode == 2
    report = json.loads(run.stdout)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


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
    cli_path = REPO / "tools/check_lifecycle_open_protection_source_parity.py"
    spec = importlib.util.spec_from_file_location("open_protection_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_open_protection_source", lambda _root: result)

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_cli_turns_audit_and_serialization_errors_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_open_protection_source_parity.py"
    spec = importlib.util.spec_from_file_location("open_protection_parity_cli_errors", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli, "audit_lifecycle_open_protection_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

    original_dumps = cli.json.dumps
    calls = 0

    def dumps(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("serialization boom")
        return original_dumps(*args, **kwargs)

    monkeypatch.setattr(cli, "audit_lifecycle_open_protection_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

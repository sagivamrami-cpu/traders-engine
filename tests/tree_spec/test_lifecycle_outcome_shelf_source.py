"""Contract tests for the inert outcome/shelf retained-source audit."""
from __future__ import annotations

import ast
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_outcome_shelf.py"


def api():
    name = "trading_system.tree_spec.lifecycle_outcome_shelf_source"
    assert importlib.util.find_spec(name) is not None, "lifecycle outcome/shelf source auditor missing"
    return importlib.import_module(name)


def test_complete_projection_and_actual_admission_gate_children_verify():
    report = api().audit_lifecycle_outcome_shelf_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] and report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_outcome_shelf"]
    assert report["dependencies"]["tracker_admission"]["checked_projections"] == [
        "trading_system/tree_replay/_vendor/tracker_admission.py",
        "trading_system/tree_replay/_vendor/tracker_symbols.py",
        "trading_system/tree_replay/_vendor/pricing.py",
        "trading_system/tree_replay/_vendor/basis_symbols.py",
        "trading_system/tree_replay/_vendor/quarters.py",
        "trading_system/tree_replay/_vendor/admission_quality.py",
        "trading_system/tree_replay/_vendor/admission_swing.py",
    ]
    assert report["dependencies"]["lifecycle_gate"]["checked_projections"] == [
        "lifecycle_gate"
    ]
    assert not report["ready_for_replay"] and not report["ready_for_training"]


def test_runtime_and_audit_pin_physical_selected_source_order():
    module = api()
    expected = (
        "OUTCOMES", "EXPIRE_H", "EXPIRE_BY_STYLE", "_outcome", "_atomic_json",
        "has_open", "_expire_h", "SHELF", "SHELF_MAX_H",
        "REVIVAL_COOLDOWN_S", "_shelve",
    )
    assert module.SYMBOLS == expected
    runtime = ast.parse((REPO / module.VENDOR).read_text(encoding="utf-8"))
    cls = next(node for node in runtime.body if isinstance(node, ast.ClassDef))
    names = [
        node.name if isinstance(node, ast.FunctionDef) else node.targets[0].id
        for node in cls.body
        if isinstance(node, ast.FunctionDef)
        or (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name))
    ]
    assert names == [
        "OUTCOMES", "EXPIRE_H", "EXPIRE_BY_STYLE", "__init__", "_outcome",
        "_atomic_json", "has_open", "_expire_h", "SHELF", "SHELF_MAX_H",
        "REVIVAL_COOLDOWN_S", "_shelve",
    ]


def test_missing_retained_root_fails_closed_without_readiness(tmp_path):
    report = api().audit_lifecycle_outcome_shelf_source(tmp_path / "missing")

    assert report["status"] == "BLOCKED"
    assert report["blockers"] and not report["source_subset_verified"]
    assert not report["ready_for_replay"] and not report["ready_for_training"]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("PurePosixPath(\"chart-desk/out/trade_outcomes.jsonl\")", "PurePosixPath(\"outcomes.jsonl\")"),
        ("self.source.now_epoch()", "time.time()"),
        ("self.source.outcomes_mkdir(self.OUTCOMES.parent.as_posix(),", "self.source.atomic_mkdir(self.OUTCOMES.parent.as_posix(),"),
        ("return self.admission.has_open(symbol, direction, state=state)", "return False"),
        ("if \"tree\" in (t.get(\"variant\") or \"\"):", "if False:"),
        ("self.source.atomic_replace(tmp, path.as_posix())", "self.source.atomic_replace(path.as_posix(), tmp)"),
    ],
)
def test_audit_rejects_artifact_clock_io_child_binding_and_branch_drift(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_outcome_shelf.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_outcome_shelf" in report["blockers"]
    assert not report["source_subset_verified"]


def test_audit_rejects_source_pin_symbol_order_and_signature_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "SYMBOLS", tuple(reversed(module.SYMBOLS)))
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert any("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH" in row for row in report["blockers"])

    monkeypatch.undo()
    signatures = list(module.SIGNATURES)
    signatures[-1] = "def _atomic_json(path, obj: dict) -> None: pass"
    monkeypatch.setattr(module, "SIGNATURES", tuple(signatures))
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert any("SOURCE_SIGNATURE_MISMATCH:_atomic_json" in row for row in report["blockers"])


def test_child_contract_identity_and_required_projections_are_immutable_and_enforced(monkeypatch):
    module = api()
    with pytest.raises(TypeError):
        module._EXPECTED_CHILD_AUDITS[0] = ("tampered",)
    with pytest.raises(TypeError):
        module._REQUIRED_CHILD_PROJECTIONS[0] = ("tampered",)

    monkeypatch.setitem(
        module.CHILD_AUDITS,
        "tracker_admission",
        (
            "trading_system.tree_spec.tracker_lifecycle_caller_source",
            "audit_tracker_lifecycle_caller_source",
        ),
    )
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:tracker_admission" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setitem(module.CHILD_AUDITS, "unexpected", ("x", "y"))
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:SET" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(
        module,
        "_child_audit",
        lambda _name, _root: {
            "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
            "checked_projections": ["wrong"], "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False, "ready_for_training": False,
        },
    )
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "DEPENDENCY:tracker_admission:UNREADABLE:TypeError" in report["blockers"]


@pytest.mark.parametrize(
    "child",
    [
        {"source_subset_verified": "yes", "blockers": []},
        {"source_subset_verified": True, "blockers": ()},
        {"source_subset_verified": True, "blockers": [object()]},
        {"status": "VERIFIED", "source_subset_verified": True, "blockers": [], "bad": object()},
    ],
)
def test_malformed_or_unserializable_child_report_fails_closed(monkeypatch, child):
    module = api()
    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: child)

    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)

    assert "DEPENDENCY:tracker_admission:UNREADABLE:TypeError" in report["blockers"]
    assert not report["source_subset_verified"]


def test_blocked_and_raised_child_reports_fail_closed(monkeypatch):
    module = api()
    monkeypatch.setattr(
        module,
        "_child_audit",
        lambda _name, _root: {"status": "BLOCKED", "source_subset_verified": False, "blockers": ["CHILD_DRIFT"]},
    )
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "DEPENDENCY:tracker_admission:CHILD_DRIFT" in report["blockers"]

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: (_ for _ in ()).throw(RuntimeError("unavailable")))
    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)
    assert "DEPENDENCY:tracker_admission:UNREADABLE:RuntimeError" in report["blockers"]


def test_audit_exception_fails_closed(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "_projection", lambda _text: (_ for _ in ()).throw(RuntimeError("bad audit")))

    report = module.audit_lifecycle_outcome_shelf_source(RETAINED)

    assert any("SOURCE_PROJECTION_UNREADABLE:lifecycle_outcome_shelf:RuntimeError" in row for row in report["blockers"])


def test_explicit_root_cli_runs_from_an_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_outcome_shelf_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED" and report["blockers"] == []
    assert not report["ready_for_replay"] and not report["ready_for_training"]


def test_cli_fails_closed_for_missing_root_and_unexpected_audit_error(tmp_path, monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_outcome_shelf_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli_path), "--source-root", str(tmp_path / "missing")],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "BLOCKED"

    spec = importlib.util.spec_from_file_location("outcome_shelf_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_outcome_shelf_source", lambda _root: (_ for _ in ()).throw(RuntimeError("unexpected")))
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_turns_unserializable_or_serialization_error_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_outcome_shelf_source_parity.py"
    spec = importlib.util.spec_from_file_location("outcome_shelf_parity_cli_serialization", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_outcome_shelf_source",
        lambda _root: {"status": "VERIFIED", "source_subset_verified": True, "blockers": [], "bad": object()},
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:TypeError"]

    original_dumps = cli.json.dumps
    calls = 0

    def dumps(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("serialization boom")
        return original_dumps(*args, **kwargs)

    monkeypatch.setattr(cli, "audit_lifecycle_outcome_shelf_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_turns_a_malformed_audit_result_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_outcome_shelf_source_parity.py"
    spec = importlib.util.spec_from_file_location("outcome_shelf_parity_cli_malformed", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_outcome_shelf_source", lambda _root: "not a report")

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:TypeError"]


def test_cli_turns_a_contradictory_verified_report_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_outcome_shelf_source_parity.py"
    spec = importlib.util.spec_from_file_location("outcome_shelf_parity_cli_contradictory", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_outcome_shelf_source",
        lambda _root: {
            "status": "VERIFIED", "source_subset_verified": True,
            "blockers": ["CONTRADICTION"], "checked_projections": [],
            "dependencies": {}, "source_commits": {},
            "ready_for_replay": False, "ready_for_training": False,
        },
    )

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:TypeError"]

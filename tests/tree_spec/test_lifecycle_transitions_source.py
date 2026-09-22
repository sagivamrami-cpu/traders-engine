"""Independent source-proof contract for tracker lifecycle transitions."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_transitions.py"


def api():
    name = "trading_system.tree_spec.lifecycle_transitions_source"
    assert importlib.util.find_spec(name) is not None, "lifecycle transitions source auditor missing"
    return importlib.import_module(name)


def test_complete_transition_projection_and_actual_lifecycle_primitives_audit_verify():
    result = api().audit_lifecycle_transitions_source(RETAINED)

    assert result["status"] == "VERIFIED"
    assert result["source_subset_verified"] and result["blockers"] == []
    assert result["checked_projections"] == ["lifecycle_transitions"]
    child = result["dependencies"]["lifecycle_primitives"]
    assert child["status"] == "VERIFIED"
    assert child["checked_projections"] == [
        "lifecycle_bars", "desk_success", "lifecycle_voice"
    ]
    assert not result["ready_for_replay"] and not result["ready_for_training"]


def test_missing_retained_root_fails_closed_without_readiness(tmp_path):
    result = api().audit_lifecycle_transitions_source(tmp_path / "missing")

    assert result["status"] == "BLOCKED"
    assert result["blockers"] and not result["source_subset_verified"]
    assert not result["ready_for_replay"] and not result["ready_for_training"]


def test_explicit_root_cli_runs_from_an_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_transitions_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED" and report["blockers"] == []
    assert not report["ready_for_replay"] and not report["ready_for_training"]


def test_cli_fails_closed_as_json_for_missing_explicit_root(tmp_path):
    cli = REPO / "tools/check_lifecycle_transitions_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(tmp_path / "missing")],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "old,new",
    [
        ("self.desk_success = DeskSuccess(source)", "self.desk_success = source"),
        ("self.source.now_epoch()", "time.time()"),
        ("self._progress_pct(t[\"symbol\"])", "_progress_pct(t[\"symbol\"])"),
        ("self._tp_management_line(i, len(t[\"targets\"]))", "_tp_management_line(i, len(t[\"targets\"]))"),
        ("self._no_score(why)", "_no_score(why)"),
        ("from .lifecycle_bars import _entry_band", "from .pricing import entry_zone"),
    ],
)
def test_audit_rejects_internal_binding_clock_and_dependency_substitution_drift(
    tmp_path, monkeypatch, old, new
):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_transitions.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    result = module.audit_lifecycle_transitions_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_transitions" in result["blockers"]
    assert not result["source_subset_verified"]


@pytest.mark.parametrize(
    "old,new",
    [
        ("return next((v for k, v in self.PROGRESS_PCT.items() if k in u), 0.10)",
         "return next((v for k, v in self.PROGRESS_PCT.items() if k in u), 0.11)"),
        ("if i >= total:", "if i > total:"),
        ("if gain <= 0:", "if gain < 0:"),
        ("if f\"TP{i}\" not in t[\"hit\"]", "if True"),
    ],
)
def test_audit_rejects_selected_constant_text_and_branch_drift(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_transitions.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    result = module.audit_lifecycle_transitions_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_transitions" in result["blockers"]


def test_audit_rejects_selected_source_order_and_signature_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "SYMBOLS", tuple(reversed(module.SYMBOLS)))

    result = module.audit_lifecycle_transitions_source(RETAINED)

    assert any(
        row.startswith("SOURCE_PROJECTION_UNREADABLE:lifecycle_transitions:ValueError:SOURCE_SYMBOL_ORDER")
        for row in result["blockers"]
    )

    monkeypatch.undo()
    signatures = list(module.SIGNATURES)
    signatures[-1] = "def _cancel_line(t: dict, why: int) -> str: pass"
    monkeypatch.setattr(module, "SIGNATURES", tuple(signatures))
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert any("SOURCE_SIGNATURE_MISMATCH:_cancel_line" in row for row in result["blockers"])


def test_audit_rejects_authority_commit_and_blob_pin_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in result["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in result["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in result["blockers"]


def test_audit_propagates_actual_child_failure_and_fails_closed(monkeypatch):
    module = api()
    original = module._child_audit

    def child(name, root):
        if name == "lifecycle_primitives":
            return {"source_subset_verified": False, "blockers": ["CHILD_DRIFT"]}
        return original(name, root)

    monkeypatch.setattr(module, "_child_audit", child)
    result = module.audit_lifecycle_transitions_source(RETAINED)

    assert "DEPENDENCY:lifecycle_primitives:CHILD_DRIFT" in result["blockers"]
    assert not result["source_subset_verified"]


def test_audit_rejects_child_audit_identity_and_required_projection_drift(monkeypatch):
    module = api()
    with pytest.raises(TypeError):
        module._EXPECTED_CHILD_AUDITS[0] = ("tampered",)

    monkeypatch.setitem(
        module.CHILD_AUDITS,
        "lifecycle_primitives",
        (
            "trading_system.tree_spec.tracker_lifecycle_caller_source",
            "audit_tracker_lifecycle_caller_source",
        ),
    )
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:lifecycle_primitives" in result["blockers"]

    monkeypatch.undo()
    monkeypatch.setitem(
        module.CHILD_AUDITS,
        "unexpected",
        module.CHILD_AUDITS["lifecycle_primitives"],
    )
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:SET" in result["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(
        module,
        "_child_audit",
        lambda _name, _root: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": ["lifecycle_bars"],
            "dependencies": {},
            "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False,
            "ready_for_training": False,
        },
    )
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "DEPENDENCY:lifecycle_primitives:UNREADABLE:TypeError" in result["blockers"]


@pytest.mark.parametrize(
    "report",
    [
        {"source_subset_verified": "yes", "blockers": []},
        {"source_subset_verified": True, "blockers": ()},
        {"source_subset_verified": True, "blockers": [object()]},
    ],
)
def test_audit_turns_missing_raised_or_malformed_child_reports_into_blockers(monkeypatch, report):
    module = api()

    def child(name, _root):
        if name == "lifecycle_primitives":
            return report
        raise AssertionError(name)

    monkeypatch.setattr(module, "_child_audit", child)
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "DEPENDENCY:lifecycle_primitives:UNREADABLE:TypeError" in result["blockers"]

    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: (_ for _ in ()).throw(RuntimeError("unavailable")))
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "DEPENDENCY:lifecycle_primitives:UNREADABLE:RuntimeError" in result["blockers"]


def test_audit_and_cli_fail_closed_for_unserializable_child_report(monkeypatch, capsys):
    module = api()
    monkeypatch.setattr(
        module,
        "_child_audit",
        lambda _name, _root: {
            "source_subset_verified": True,
            "blockers": [],
            "unserializable": object(),
        },
    )
    result = module.audit_lifecycle_transitions_source(RETAINED)
    assert "DEPENDENCY:lifecycle_primitives:UNREADABLE:TypeError" in result["blockers"]

    cli_path = REPO / "tools/check_lifecycle_transitions_source_parity.py"
    spec = importlib.util.spec_from_file_location("transitions_parity_cli_unserializable", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_transitions_source",
        lambda _root: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "unserializable": object(),
        },
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:TypeError"]


def test_cli_turns_unexpected_serialization_error_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_transitions_source_parity.py"
    spec = importlib.util.spec_from_file_location("transitions_parity_cli_serialization", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_transitions_source",
        lambda _root: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": [],
            "dependencies": {},
            "source_commits": {},
            "ready_for_replay": False,
            "ready_for_training": False,
        },
    )
    original_dumps = cli.json.dumps
    calls = 0

    def dumps(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("serialization boom")
        return original_dumps(*args, **kwargs)

    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_turns_unexpected_audit_error_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_transitions_source_parity.py"
    spec = importlib.util.spec_from_file_location("transitions_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_transitions_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

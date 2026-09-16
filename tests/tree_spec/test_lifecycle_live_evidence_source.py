"""Contract tests for the inert live-evidence retained-source audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_live_evidence.py"


def api():
    name = "trading_system.tree_spec.lifecycle_live_evidence_source"
    assert importlib.util.find_spec(name) is not None, "lifecycle live-evidence source auditor missing"
    return importlib.import_module(name)


def test_complete_projection_verifies_and_never_claims_readiness():
    report = api().audit_lifecycle_live_evidence_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_live_evidence"]
    assert report["dependencies"] == {}
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_audit_and_runtime_preserve_exact_selected_source_order():
    module = api()
    expected = (
        "QUOTE_MAX_AGE_S", "_live_prices", "_historical_replay_safe",
        "FORCE_BAR_AGE_S",
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
        "__init__", "QUOTE_MAX_AGE_S", "_live_prices",
        "_historical_replay_safe", "FORCE_BAR_AGE_S",
    ]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("QUOTE_MAX_AGE_S = 420.0", "QUOTE_MAX_AGE_S = 419.0"),
        ("self.source.quote_payload()", "json.loads(QUOTES.read_text())"),
        ("self.source.now_epoch()", "time.time()"),
        ("except Exception:\n            return out", "except ValueError:\n            return out"),
        ("except Exception:\n                continue", "except ValueError:\n                continue"),
        ("except (IndexError, KeyError, TypeError, ValueError):", "except Exception:"),
        ("FORCE_BAR_AGE_S = 120.0", "FORCE_BAR_AGE_S = 121.0"),
    ],
)
def test_audit_rejects_constant_adaptation_and_error_boundary_drift(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_live_evidence.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_live_evidence_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_live_evidence" in report["blockers"]
    assert report["source_subset_verified"] is False


def test_audit_rejects_source_identity_blob_order_and_signature_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_live_evidence_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_live_evidence_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "SYMBOLS", tuple(reversed(module.SYMBOLS)))
    report = module.audit_lifecycle_live_evidence_source(RETAINED)
    assert any("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH" in row for row in report["blockers"])

    monkeypatch.undo()
    signatures = list(module.SIGNATURES)
    signatures[-1] = "def _historical_replay_safe(df, corr, t) -> bool: pass"
    monkeypatch.setattr(module, "SIGNATURES", tuple(signatures))
    report = module.audit_lifecycle_live_evidence_source(RETAINED)
    assert any("SOURCE_SIGNATURE_MISMATCH:_historical_replay_safe" in row for row in report["blockers"])


def test_missing_retained_root_and_projection_exception_fail_closed(tmp_path, monkeypatch):
    module = api()
    report = module.audit_lifecycle_live_evidence_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["blockers"] and report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False

    monkeypatch.setattr(module, "_projection", lambda _text: (_ for _ in ()).throw(RuntimeError("bad audit")))
    report = module.audit_lifecycle_live_evidence_source(RETAINED)
    assert any("SOURCE_PROJECTION_UNREADABLE:lifecycle_live_evidence:RuntimeError" in row for row in report["blockers"])


def test_explicit_root_cli_verifies_from_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_live_evidence_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED" and report["blockers"] == []
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
def test_cli_turns_malformed_contradictory_or_unserializable_result_into_blocked_json(monkeypatch, capsys, result):
    cli_path = REPO / "tools/check_lifecycle_live_evidence_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_evidence_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_live_evidence_source", lambda _root: result)

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_cli_turns_audit_and_serialization_errors_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_live_evidence_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_evidence_parity_cli_error", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli, "audit_lifecycle_live_evidence_source",
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

    monkeypatch.setattr(cli, "audit_lifecycle_live_evidence_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

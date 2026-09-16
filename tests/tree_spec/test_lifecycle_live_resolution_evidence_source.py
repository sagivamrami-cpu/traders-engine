"""Contract tests for live-resolution evidence retained-source audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py"


def api():
    name = "trading_system.tree_spec.lifecycle_live_resolution_evidence_source"
    assert importlib.util.find_spec(name) is not None, (
        "lifecycle live-resolution evidence source auditor missing"
    )
    return importlib.import_module(name)


def test_complete_fragment_projection_verifies_exact_runtime_and_never_claims_readiness():
    report = api().audit_lifecycle_live_resolution_evidence_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == ["lifecycle_live_resolution_evidence"]
    assert report["dependencies"] == {}
    assert report["source_commits"] == {
        "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
    }
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('in ("PENDING", "OPEN")', 'in ("PENDING",)'),
        ("self.FORCE_BAR_AGE_S", "119.0"),
        ('self.source.fetch_corrected(symbol, "15m", 2)',
         'self.source.fetch_corrected(symbol, "5m", 2)'),
        ('getattr(correction, "unverified", False)', "False"),
        ('getattr(correction, "source", "") == "tv_stale"', "False"),
        ("latest > now - age", "latest >= now - age"),
        ('bars["low"].iloc[-1]', 'bars["close"].iloc[-1]'),
        ('bars["high"].iloc[-1]', 'bars["close"].iloc[-1]'),
        ("except Exception:\n                continue", "except ValueError:\n                continue"),
    ],
)
def test_audit_rejects_runtime_filter_fallback_guard_timestamp_range_and_boundary_drift(
    tmp_path, monkeypatch, old, new
):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_live_resolution_evidence.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_live_resolution_evidence_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_live_resolution_evidence" in report["blockers"]
    assert report["source_subset_verified"] is False


def test_extraction_requires_complete_physical_order_and_source_invariants():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")
    fragment = module._extract_fragment(source)
    assert module._fragment_names(fragment) == (
        "prices", "_bar_extremes", "try", "_now", "for", "if_not_prices"
    )

    moved = source.replace("    _now = time.time()\n", "", 1)
    with pytest.raises(ValueError, match="SOURCE_FRAGMENT_ORDER_MISMATCH"):
        module._extract_fragment(moved)


def test_audit_rejects_pin_blob_and_projection_failures(monkeypatch, tmp_path):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_live_resolution_evidence_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_live_resolution_evidence_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    report = module.audit_lifecycle_live_resolution_evidence_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False

    monkeypatch.setattr(
        module, "_projection", lambda _text: (_ for _ in ()).throw(RuntimeError("bad audit"))
    )
    report = module.audit_lifecycle_live_resolution_evidence_source(RETAINED)
    assert any(
        row.startswith("SOURCE_PROJECTION_UNREADABLE:lifecycle_live_resolution_evidence:RuntimeError")
        for row in report["blockers"]
    )


def test_explicit_root_cli_verifies_from_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_live_resolution_evidence_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
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
    cli_path = REPO / "tools/check_lifecycle_live_resolution_evidence_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_resolution_evidence_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_live_resolution_evidence_source", lambda _root: result)

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_cli_turns_audit_and_serialization_errors_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_live_resolution_evidence_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_resolution_evidence_parity_cli_errors", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_live_resolution_evidence_source",
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

    monkeypatch.setattr(cli, "audit_lifecycle_live_resolution_evidence_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

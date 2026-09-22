"""Contract tests for the retained-source closed-bar lifecycle resolver audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_closed_resolver.py"


def api():
    name = "trading_system.tree_spec.lifecycle_closed_resolver_source"
    assert importlib.util.find_spec(name) is not None, "closed resolver source auditor missing"
    return importlib.import_module(name)


def verified_child_reports(module):
    required = dict(module._REQUIRED_CHILD_PROJECTIONS)
    return {
        name: {
            "status": "VERIFIED",
            "source_subset_verified": True,
            "blockers": [],
            "checked_projections": list(required[name]),
            "dependencies": {},
            "source_commits": {"chart-desk": module.COMMIT},
            "ready_for_replay": False,
            "ready_for_training": False,
        }
        for name in module.CHILD_AUDITS
    }


def test_closed_resolver_projection_and_direct_children_verify_without_readiness():
    report = api().audit_lifecycle_closed_resolver_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == [
        "lifecycle_closed_resolver_source_kernel",
        "lifecycle_closed_resolver",
    ]
    assert tuple(report["dependencies"]) == (
        "lifecycle_closed_pending_resolution",
        "lifecycle_primitives",
        "lifecycle_outcome_shelf",
        "lifecycle_transitions",
        "tree_revalidation",
        "lifecycle_open_protection",
        "lifecycle_open_ordinary_resolution",
    )
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("\"15m\", 3", "\"15m\", 2"),
        ("getattr(correction, \"unverified\", False)", "False"),
        ("getattr(correction, \"source\", \"\") == \"tv_stale\"", "False"),
        ("timestamp.timestamp() > float(trade[\"ts\"])", "timestamp.timestamp() >= float(trade[\"ts\"])"),
        ("extrema = _open_extremes(since, trade)", "extrema = (high, low)"),
        ("if trade.get(\"state\") != \"OPEN\":\n                continue", "if trade.get(\"state\") != \"OPEN\":\n                return messages, changed"),
        ("minimum_message = self.desk_success.observe_bars(trade, since)", "minimum_message = None"),
        ("child_messages, child_changed = self.protection.resolve(trade, low=low, high=high)", "child_messages, child_changed = self.ordinary.resolve(\n            trade, low=low, high=high, minimum_message=minimum_message\n        )"),
        ("if child_changed:\n            return messages, changed", "if child_changed:\n            pass"),
        ("self.ordinary.resolve(\n            trade, low=low, high=high, minimum_message=minimum_message\n        )", "self.zone_return.resolve(trade, spot=high)"),
    ],
)
def test_audit_rejects_fetch_correction_slice_extrema_order_and_zone_return_mutations(
    tmp_path, monkeypatch, old, new
):
    module = api()
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_closed_resolver.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))

    report = module.audit_lifecycle_closed_resolver_source(RETAINED)

    assert "VENDOR_AST_MISMATCH:lifecycle_closed_resolver" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_source_kernel_requires_unique_closed_loop_and_physical_pending_open_order():
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")

    assert module._kernel_names(module._extract_closed_kernel(source)) == (
        "corrected_fetch",
        "correction_gates",
        "strict_since_slice",
        "prefill_extrema",
        "postfill_extrema",
        "pending_branch",
        "open_branch",
    )

    changed = source.replace('if t["state"] == "PENDING":', 'if t["state"] == "OPEN":', 1)
    with pytest.raises(ValueError, match="SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH"):
        module._extract_closed_kernel(changed)


def test_child_identity_source_identity_and_malformed_reports_fail_closed(monkeypatch, tmp_path):
    module = api()
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])
    actual_commit = module.COMMIT
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_closed_resolver_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.setattr(module, "COMMIT", actual_commit)
    actual_blob = module.BLOB
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_closed_resolver_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.setattr(module, "BLOB", actual_blob)
    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"status": "VERIFIED"})
    report = module.audit_lifecycle_closed_resolver_source(RETAINED)
    assert "DEPENDENCY:lifecycle_closed_pending_resolution:UNREADABLE:TypeError" in report["blockers"]

    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])
    monkeypatch.setattr(module, "CHILD_AUDITS", {})
    report = module.audit_lifecycle_closed_resolver_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:SET" in report["blockers"]

    monkeypatch.setattr(
        module,
        "CHILD_AUDITS",
        {row[0]: tuple(row[1:]) for row in module._EXPECTED_CHILD_AUDITS},
    )
    report = module.audit_lifecycle_closed_resolver_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_cli_requires_explicit_root_and_emits_schema_valid_blocked_json(capsys, monkeypatch):
    cli_path = REPO / "tools/check_lifecycle_closed_resolver_source_parity.py"
    spec = importlib.util.spec_from_file_location("closed_resolver_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "BLOCKED"
    assert missing["ready_for_replay"] is False
    assert missing["ready_for_training"] is False

    monkeypatch.setattr(
        cli,
        "audit_lifecycle_closed_resolver_source",
        lambda _root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]


def test_cli_verifies_from_an_unrelated_cwd_and_fails_closed_for_missing_root(tmp_path):
    cli = REPO / "tools/check_lifecycle_closed_resolver_source_parity.py"
    good = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert good.returncode == 0, good.stderr
    good_report = json.loads(good.stdout)
    assert good_report["status"] == "VERIFIED"
    assert good_report["ready_for_replay"] is False
    assert good_report["ready_for_training"] is False

    bad = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(tmp_path / "missing")],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert bad.returncode == 2
    assert json.loads(bad.stdout)["status"] == "BLOCKED"

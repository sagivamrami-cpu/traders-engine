"""Contract tests for the retained-source live PENDING/OPEN resolver audit."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor/lifecycle_live_resolver.py"


def api():
    name = "trading_system.tree_spec.lifecycle_live_resolver_source"
    assert importlib.util.find_spec(name) is not None, "lifecycle live-resolver source auditor missing"
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


def mutate_live_kernel(source, old, new):
    start = source.index("def _check_live_locked")
    return source[:start] + source[start:].replace(old, new, 1)


def test_complete_live_resolver_projection_and_child_graph_verify_without_readiness():
    report = api().audit_lifecycle_live_resolver_source(RETAINED)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == [
        "lifecycle_live_resolver_source_kernel",
        "lifecycle_live_resolver",
    ]
    assert tuple(report["dependencies"]) == (
        "lifecycle_live_evidence",
        "lifecycle_pending_resolution",
        "lifecycle_open_postfill_evidence",
        "lifecycle_open_minimum_success",
        "lifecycle_open_protection",
        "lifecycle_open_ordinary_resolution",
        "lifecycle_open_zone_return",
    )
    assert report["source_commits"] == {"chart-desk": api().COMMIT}
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("prices = _live_prices()\n    _bar_extremes: dict = {}", "_bar_extremes: dict = {}\n    prices = _live_prices()"),
        ("except Exception:\n        _q = {}\n    _now", "except OSError:\n        _q = {}\n    _now"),
        ("_age <= FORCE_BAR_AGE_S", "_age < FORCE_BAR_AGE_S"),
        ("_bar_ts > (_now - _age)", "_bar_ts >= (_now - _age)"),
        ("float(_df[\"low\"].iloc[-1]),\n                                     float(_df[\"high\"].iloc[-1])", "float(_df[\"high\"].iloc[-1]),\n                                     float(_df[\"low\"].iloc[-1])"),
        ("prices[_s] = float(_df[\"close\"].iloc[-1])", "prices[_s] = float(_df[\"high\"].iloc[-1])"),
        ("for key, t in list(d.items()):", "for key, t in d.items():"),
        ('("STOPPED", "DONE", "CANCELLED")', '("STOPPED", "DONE")'),
        ('if t["state"] == "PENDING":', 'if t["state"] == "OPEN":'),
        ("if _ambiguous_touch(t, _lo, _hi, short, protective):", "if False:"),
        ("else:\n                # Only the live path says this:", "if False:\n                # Only the live path says this:"),
    ],
)
def test_source_kernel_rejects_quote_fallback_scan_and_branch_precedence_mutations(old, new):
    module = api()
    source = (RETAINED / "chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")
    assert old in source

    with pytest.raises(ValueError, match="SOURCE_LIVE_RESOLVER_KERNEL_MISMATCH"):
        module._extract_source_kernel(mutate_live_kernel(source, old, new))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("raw_quotes = self.source.quote_payload()\n        except Exception:", "raw_quotes = self.source.quote_payload()\n            raw_quotes = self.source.quote_payload()\n        except Exception:"),
        ("quote=raw_quotes.get(symbol) or {},", "quote={},"),
        ("if trade.get(\"state\") == \"CANCELLED\":\n                    continue", "if False:\n                    continue"),
        ("self.protection.resolve(trade, low=low, high=high)", "self.ordinary.resolve(trade, low=low, high=high, minimum_message=minimum_message)"),
        ('if trade.get("state") == "OPEN":\n                child_messages, child_changed = self.zone_return.resolve', 'if trade.get("state") == "DONE":\n                child_messages, child_changed = self.zone_return.resolve'),
        ("return messages, changed", "self.source.save(state)\n        return messages, changed"),
    ],
)
def test_runtime_rejects_observation_raw_quote_order_and_effect_boundary_drift(tmp_path, monkeypatch, old, new):
    module = api()
    text = VENDOR.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "lifecycle_live_resolver.py"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    monkeypatch.setattr(module, "VENDOR", str(mutated))
    reports = verified_child_reports(module)
    monkeypatch.setattr(module, "_child_audit", lambda name, _root: reports[name])

    report = module.audit_lifecycle_live_resolver_source(RETAINED)

    assert report["status"] == "BLOCKED"
    assert "VENDOR_AST_MISMATCH:lifecycle_live_resolver" in report["blockers"]
    assert report["source_subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_source_identity_root_blob_child_identity_and_malformed_child_fail_closed(monkeypatch, tmp_path):
    module = api()
    monkeypatch.setattr(module, "COMMIT", "0" * 40)
    report = module.audit_lifecycle_live_resolver_source(RETAINED)
    assert "BASELINE_COMMIT_MISMATCH" in report["blockers"]
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.audit_lifecycle_live_resolver_source(RETAINED)
    assert "SOURCE_BLOB_MISMATCH:tracker.py" in report["blockers"]

    monkeypatch.undo()
    report = module.audit_lifecycle_live_resolver_source(tmp_path / "missing")
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

    monkeypatch.setattr(module, "CHILD_AUDITS", {})
    report = module.audit_lifecycle_live_resolver_source(RETAINED)
    assert "CHILD_AUDIT_IDENTITY_MISMATCH:SET" in report["blockers"]

    monkeypatch.undo()
    monkeypatch.setattr(module, "_child_audit", lambda _name, _root: {"bad": "report"})
    report = module.audit_lifecycle_live_resolver_source(RETAINED)
    assert any(row.startswith("DEPENDENCY:") for row in report["blockers"])


def test_explicit_root_cli_verifies_from_unrelated_directory(tmp_path):
    cli = REPO / "tools/check_lifecycle_live_resolver_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "VERIFIED" and report["blockers"] == []
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


@pytest.mark.parametrize("args", [[], ["--source-root", "C:/missing-live-resolver-root"]])
def test_cli_fails_closed_as_json_for_missing_or_invalid_explicit_root(tmp_path, args):
    cli = REPO / "tools/check_lifecycle_live_resolver_source_parity.py"
    run = subprocess.run(
        [sys.executable, "-B", str(cli), *args],
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
def test_cli_turns_malformed_contradictory_and_unserializable_audits_into_blocked_json(monkeypatch, capsys, result):
    cli_path = REPO / "tools/check_lifecycle_live_resolver_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_resolver_parity_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "audit_lifecycle_live_resolver_source", lambda _root: result)

    assert cli.main(["--source-root", str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert report["blockers"]
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_cli_turns_audit_and_serialization_errors_into_blocked_json(monkeypatch, capsys):
    cli_path = REPO / "tools/check_lifecycle_live_resolver_source_parity.py"
    spec = importlib.util.spec_from_file_location("live_resolver_parity_cli_errors", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "audit_lifecycle_live_resolver_source",
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

    monkeypatch.setattr(cli, "audit_lifecycle_live_resolver_source", lambda _root: {
        "status": "VERIFIED", "source_subset_verified": True, "blockers": [],
        "checked_projections": [], "dependencies": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    })
    monkeypatch.setattr(cli.json, "dumps", dumps)
    assert cli.main(["--source-root", str(RETAINED)]) == 2
    assert json.loads(capsys.readouterr().out)["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]

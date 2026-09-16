"""Tests for the static closed-bar causal replay source intake."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
RETAINED_ROOT = Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts"))
SOURCE = RETAINED_ROOT / "chart-desk" / "scripts" / "market_watch.py"


def api():
    name = "trading_system.tree_spec.causal_replay_source"
    assert importlib.util.find_spec(name) is not None, "causal replay source auditor missing"
    return importlib.import_module(name)


def blob(text: str) -> str:
    raw = text.encode("utf-8")
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def mutated_audit(monkeypatch, old: str, new: str, *, occurrence: int = 1):
    module = api()
    original = SOURCE.read_text(encoding="utf-8")
    assert original.count(old) >= occurrence
    before, separator, after = original.rpartition(old) if occurrence == -1 else original.partition(old)
    changed = before + new + after
    assert changed != original
    real_read_text = Path.read_text

    def read_text(path, *args, **kwargs):
        if path.resolve() == SOURCE.resolve():
            return changed
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(module, "BLOB", blob(changed))
    return module.check_source_parity(RETAINED_ROOT)


def mutated_audit_after(monkeypatch, marker: str, old: str, new: str):
    """Mutate the first control-flow token after one named outer-gate guard."""
    module = api()
    original = SOURCE.read_text(encoding="utf-8")
    before, separator, after = original.partition(marker)
    assert separator, f"missing outer-gate marker: {marker}"
    assert old in after
    changed = before + separator + after.replace(old, new, 1)
    assert changed != original
    real_read_text = Path.read_text

    def read_text(path, *args, **kwargs):
        if path.resolve() == SOURCE.resolve():
            return changed
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(module, "BLOB", blob(changed))
    return module.check_source_parity(RETAINED_ROOT)


def assert_blocked(report):
    assert report["status"] == "BLOCKED"
    assert report["source_subset_verified"] is False
    assert isinstance(report["blockers"], list) and report["blockers"]
    assert all(isinstance(blocker, str) and blocker for blocker in report["blockers"])
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_pinned_source_projects_outer_pass_without_replay_or_training_readiness():
    report = api().check_source_parity(RETAINED_ROOT)

    assert report["status"] == "VERIFIED"
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["checked_projections"] == list(api().REQUIRED_ORDER)
    assert report["projection"]["required_order"] == list(api().REQUIRED_ORDER)
    assert report["projection"]["level_reversal_record_guard"] == "--telegram"
    assert report["projection"]["source_lines"] == {
        "watch_state_load": 494,
        "watch_state_preproducer_save": 905,
        "tracker_closed_pass": 964,
        "tracker_gate": 972,
        "level_reversal_find": 1014,
        "level_reversal_record_alert_guard": 1066,
        "level_reversal_record": 1069,
        "tree_walk": 1239,
        "engine_build": 1449,
        "watch_state_final_save": 1599,
    }
    assert set(report["projection"]["unwired_outer_admission"]) == {
        "windows", "market_closed", "producer_arbitration", "post_stop",
        "occupied_slot", "same_level",
    }
    assert set(report["projection"]["unwired_outer_admission"].values()) == {
        "UNWIRED_OUTER_ADMISSION"
    }
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "st = json.loads(STATE.read_text()) if STATE.exists() else {}",
            "st = {}",
        ),
        ("STATE.write_text(json.dumps(st))", "pass  # missing pre-producer save"),
        ("with tracker._locked(wait=30.0, skip_if_busy=True):", "with tracker._locked(wait=3.0, skip_if_busy=True):"),
        ("tracker.closeout_check() + tracker.check()", "tracker.check() + tracker.closeout_check()"),
        ("tracker.gate(_msgs)", "tracker.not_gate(_msgs)"),
        ("level_reversal.find(sym, now=pd.Timestamp(now, unit=\"s\", tz=\"UTC\"))", "level_reversal.missing(sym, now=pd.Timestamp(now, unit=\"s\", tz=\"UTC\"))"),
        ("active_reversals[sym] = plan", "pass  # producer arbitration removed"),
        ("outside = _outside()", "outside = None"),
        ("closed = _mc.entry_blocked()", "closed = None"),
        ("cool = _trk.blocked_after_stop(sym, plan.direction, plan)", "cool = None"),
        ("if _trk.has_open(sym, plan.direction):", "if False:"),
        ("same = _trk.blocked_same_level(sym, plan.direction, plan.entry)", "same = None"),
        ("if \"--telegram\" not in sys.argv:", "if \"--alerts\" not in sys.argv:"),
        ("_trk.record(plan, variant=src, to_group=True)", "_trk.not_record(plan, variant=src, to_group=True)"),
    ],
)
def test_audit_rejects_required_source_stage_and_outer_gate_mutations(monkeypatch, old, new):
    report = mutated_audit(monkeypatch, old, new)
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
    assert_blocked(report)


@pytest.mark.parametrize(
    ("gate", "old", "new"),
    [
        ("windows", "if outside:", "if False:"),
        ("market_closed", "if closed:", "if False:"),
        ("post_stop", "if cool:", "if False:"),
        (
            "occupied_slot",
            "if _trk.has_open(sym, plan.direction):",
            "if _trk.has_open(sym, plan.direction) and False:",
        ),
        ("same_level", "if same:", "if False:"),
        (
            "producer_arbitration",
            "if st.get(state_key):",
            "if st.get(state_key) and False:",
        ),
    ],
)
def test_audit_rejects_disabled_outer_gate_predicate_while_preserving_gate_call_and_line(
    monkeypatch, gate, old, new,
):
    """A future pin must not accept a gate call whose rejection predicate is disabled."""
    report = mutated_audit(monkeypatch, old, new)
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"], gate
    assert_blocked(report)


@pytest.mark.parametrize(
    ("gate", "marker"),
    [
        ("windows", "if outside:"),
        ("market_closed", "if closed:"),
        ("post_stop", "if cool:"),
        ("occupied_slot", "if _trk.has_open(sym, plan.direction):"),
        ("same_level", "if same:"),
        ("producer_arbitration", "if st.get(state_key):"),
    ],
)
def test_audit_rejects_outer_gate_when_its_rejection_continue_is_replaced(monkeypatch, gate, marker):
    """Each rejecting branch must continue the same reversal loop before record."""
    report = mutated_audit_after(monkeypatch, marker, "continue", "pass")
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"], gate
    assert_blocked(report)


def test_audit_requires_level_reversal_before_tree_and_engine(monkeypatch):
    report = mutated_audit(
        monkeypatch,
        "    active_reversals = {}",
        "    _tree.walk('source-order-probe')\n    active_reversals = {}",
    )
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
    assert_blocked(report)


def test_audit_requires_level_reversal_before_engine(monkeypatch):
    report = mutated_audit(
        monkeypatch,
        "    active_reversals = {}",
        "    tradeplan.build_all(('source-order-probe',))\n    active_reversals = {}",
    )
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
    assert_blocked(report)


def test_audit_requires_final_state_write(monkeypatch):
    report = mutated_audit(monkeypatch, "STATE.write_text(json.dumps(st))", "pass  # missing final save", occurrence=-1)
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
    assert_blocked(report)


def test_audit_rejects_blob_and_commit_pin_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, "BLOB", "0" * 40)
    report = module.check_source_parity(RETAINED_ROOT)
    assert "SOURCE_BLOB_MISMATCH:scripts/market_watch.py" in report["blockers"]
    assert_blocked(report)

    monkeypatch.undo()
    original_git = module._git
    monkeypatch.setattr(
        module,
        "_git",
        lambda repo, *args: "0" * 40 if args == ("HEAD",) else original_git(repo, *args),
    )
    report = module.check_source_parity(RETAINED_ROOT)
    assert "SOURCE_COMMIT_MISMATCH" in report["blockers"]
    assert_blocked(report)


@pytest.mark.parametrize("mutation", ("readiness", "blob", "invalid_json", "missing"))
def test_runtime_manifest_cannot_redefine_or_weaken_audit(monkeypatch, tmp_path, mutation):
    module = api()
    config = REPO / "configs/trees/causal-replay-source-contracts.json"
    local_root = tmp_path / "workspace"
    local_config = local_root / "configs/trees/causal-replay-source-contracts.json"
    local_config.parent.mkdir(parents=True)
    if mutation != "missing":
        data = json.loads(config.read_text(encoding="utf-8"))
        if mutation == "readiness":
            data["ready_for_replay"] = True
        elif mutation == "blob":
            data["market_watch"]["git_blob_sha1"] = "0" * 40
        local_config.write_text("{" if mutation == "invalid_json" else json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", local_root)

    report = module.check_source_parity(RETAINED_ROOT)
    assert "CONTRACT_MISMATCH" in report["blockers"] or any(
        blocker.startswith("CONTRACT_UNREADABLE:") for blocker in report["blockers"]
    )
    assert_blocked(report)


def test_missing_root_and_source_read_exception_fail_closed(monkeypatch, tmp_path):
    module = api()
    assert_blocked(module.check_source_parity(tmp_path / "missing"))

    monkeypatch.setattr(module, "_read_pinned_market_watch", lambda _root: (_ for _ in ()).throw(RuntimeError("boom")))
    report = module.check_source_parity(RETAINED_ROOT)
    assert report["blockers"] == ["SOURCE_READ_OR_PARSE:RuntimeError"]
    assert_blocked(report)


def test_cli_requires_explicit_root_and_blocks_exception_or_malformed_child_report(capsys, monkeypatch):
    cli_path = REPO / "tools/check_causal_replay_source_parity.py"
    spec = importlib.util.spec_from_file_location("causal_replay_source_cli", cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main([]) == 2
    assert_blocked(json.loads(capsys.readouterr().out))

    monkeypatch.setattr(cli, "check_source_parity", lambda _root: {"status": "VERIFIED"})
    assert cli.main(["--source-root", str(RETAINED_ROOT)]) == 2
    assert_blocked(json.loads(capsys.readouterr().out))

    monkeypatch.setattr(cli, "check_source_parity", lambda _root: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cli.main(["--source-root", str(RETAINED_ROOT)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["blockers"] == ["AUDIT_UNREADABLE:RuntimeError"]
    assert_blocked(report)


def test_cli_verifies_explicit_parent_root_from_unrelated_cwd(tmp_path):
    cli = REPO / "tools/check_causal_replay_source_parity.py"
    good = subprocess.run(
        [sys.executable, "-B", str(cli), "--source-root", str(RETAINED_ROOT)],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert good.returncode == 0, good.stderr
    report = json.loads(good.stdout)
    assert report["status"] == "VERIFIED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

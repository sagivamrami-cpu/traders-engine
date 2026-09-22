"""Real synthetic detector/pricer behavior and relocated, inert audit mutations."""

import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get(
    "TR_CHARTDESK_SOURCE_ROOT",
    (Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts")) / "chart-desk"),
))
SYMBOL = "OANDA:XAUUSD"
T = pd.Timestamp("2026-09-09T03:00:00Z")
VENDOR = "trading_system/tree_replay/_vendor/reversal_producer.py"
MANIFEST = "configs/trees/reversal-producer-contracts.json"


def module(name):
    assert importlib.util.find_spec(name) is not None, f"Missing assigned sidecar: {name}"
    return importlib.import_module(name)


def producer():
    return module("trading_system.tree_replay._vendor.reversal_producer")


def audit():
    return module("tools.check_reversal_producer_source_parity")


def history(tf="5m", *, short=False, confirmed=T, trailing=False):
    # Ten prior bars have volume 100 and spread-volume 1000. The vector has
    # volume 200, spread-volume 800: volume alone establishes its climax.
    count = 13 if tf == "5m" else 12
    step = pd.Timedelta(minutes=int(tf[:-1]))
    frame = pd.DataFrame(
        [[103., 108., 98., 102., 100.]] * count,
        columns=["open", "high", "low", "close", "volume"],
        index=pd.date_range(end=confirmed - step, periods=count, freq=step),
    )
    if tf == "5m":
        frame.iloc[-2] = [102., 102., 98., 99., 200.]
        frame.iloc[-1] = [99., 102., 99., 101., 100.]
    else:
        frame.iloc[-1] = [102., 102., 98., 101., 200.]
    if short:
        original = frame.copy()
        frame["open"] = 200 - original.open
        frame["close"] = 200 - original.close
        frame["high"] = 200 - original.low
        frame["low"] = 200 - original.high
    if trailing:
        frame.loc[confirmed] = [101., 102., 100., 101., 20.]
    return frame


def correction(source="tv", unverified=False):
    # Only these attributes are consumed by find. This is a supplied offline
    # correction fixture, not broker-shape or provenance certification.
    return SimpleNamespace(source=source, unverified=unverified)


DEFAULT = object()


class OfflineInputs:
    def __init__(self, *, frames=None, levels=DEFAULT, daily=DEFAULT, corrections=None):
        self.frames = frames if frames is not None else {"5m": history(), "15m": history("15m")}
        self.levels = [("PSY-LO", 100.), ("UP", 112.), ("DOWN", 88.)] if levels is DEFAULT else levels
        self.daily = correction() if daily is DEFAULT else daily
        self.corrections = corrections or {}
        self.calls = []
        self.detections = []

    def build(self, symbol):
        self.calls.append(("map", symbol))
        return self.levels, self.daily

    def fetch_corrected(self, symbol, tf, days):
        self.calls.append(("fetch", symbol, tf, days))
        value = self.frames[tf]
        if isinstance(value, Exception):
            raise value
        return value, self.corrections.get(tf, correction())

    def detect(self, symbol, tf, frame, levels, *, now, max_age_s):
        real = module("trading_system.tree_replay._vendor.level_reversal")
        events = real.detect_frame(symbol, tf, frame, levels, now=now, max_age_s=max_age_s)
        self.detections.append((tf, now, max_age_s, events))
        return events

    def find(self, now=T):
        return producer().find_at(SYMBOL, decision_time=now, source=self,
                                  map_source=self, detector=self.detect)


@pytest.mark.parametrize("levels,daily", [([], correction()), (None, correction()), ([("PSY-LO", 100)], None),
                                        ([("PSY-LO", 100)], correction(unverified=True))])
def test_daily_gate_stops_before_any_timeframe_fetch(levels, daily):
    inputs = OfflineInputs(levels=levels, daily=daily)
    assert inputs.find() is None
    assert inputs.calls == [("map", SYMBOL)]


@pytest.mark.parametrize("source", ["proxy", "replay", "none", "tv_daily"])
def test_verified_daily_source_is_not_blanket_vetoed(source):
    inputs = OfflineInputs(daily=correction(source))
    event, plan = inputs.find()
    assert (event.timeframe, event.direction, event.confirmed_at) == ("5m", "לונג", T)
    assert (plan.entry, plan.stop, plan.targets, plan.refusal) == (100., 93., [("UP", 112.)], None)


@pytest.mark.parametrize("bad", [None, correction(unverified=True), correction("none")])
@pytest.mark.parametrize("tf,other", [("5m", "15m"), ("15m", "5m")])
def test_bar_correction_gate_skips_only_affected_timeframe(bad, tf, other):
    inputs = OfflineInputs(corrections={tf: bad})
    event, _ = inputs.find()
    assert event.timeframe == other
    assert [row[0] for row in inputs.detections] == [other]


def test_requests_are_m5_then_m15_ten_days_and_use_real_clock_and_freshness():
    inputs = OfflineInputs()
    event, _ = inputs.find(T + pd.Timedelta(microseconds=1))
    assert event.timeframe == "5m"
    assert inputs.calls == [("map", SYMBOL), ("fetch", SYMBOL, "5m", 10), ("fetch", SYMBOL, "15m", 10)]
    assert [(tf, now, age) for tf, now, age, _ in inputs.detections] == [
        ("5m", T + pd.Timedelta(microseconds=1), 370.),
        ("15m", T + pd.Timedelta(microseconds=1), 370.),
    ]


@pytest.mark.parametrize("tf,other", [("5m", "15m"), ("15m", "5m")])
def test_timeframe_fetch_exception_continues_to_available_candidate(tf, other):
    inputs = OfflineInputs()
    inputs.frames[tf] = RuntimeError("offline unavailable")
    event, _ = inputs.find()
    assert event.timeframe == other
    assert inputs.calls[-1] == ("fetch", SYMBOL, "15m", 10)


def test_no_candidates_returns_none_after_both_requests():
    inputs = OfflineInputs(frames={"5m": None, "15m": None})
    assert inputs.find() is None
    assert [row[0] for row in inputs.detections] == ["5m", "15m"]


def test_equal_confirmation_selects_m5_even_with_opposite_m15():
    inputs = OfflineInputs(frames={"5m": history(), "15m": history("15m", short=True)})
    event, plan = inputs.find()
    assert (event.timeframe, event.direction, plan.direction) == ("5m", "לונג", "לונג")
    assert [(rows[0].timeframe, rows[0].direction) for _, _, _, rows in inputs.detections] == [
        ("5m", "לונג"), ("15m", "שורט")]


def test_newer_m15_beats_older_fresh_m5():
    inputs = OfflineInputs(frames={"5m": history(confirmed=T - pd.Timedelta(minutes=5)),
                                    "15m": history("15m", short=True)})
    event, plan = inputs.find()
    assert (event.timeframe, event.confirmed_at, plan.direction) == ("15m", T, "שורט")


def test_older_confirmation_survives_latest_nonsignal_bar():
    inputs = OfflineInputs(frames={"5m": history(confirmed=T - pd.Timedelta(minutes=5), trailing=True),
                                    "15m": None})
    event, _ = inputs.find()
    assert event.confirmed_at == pd.Timestamp("2026-09-09T02:55:00Z")
    assert event.confirmation_open_time == pd.Timestamp("2026-09-09T02:50:00Z")


@pytest.mark.parametrize("tf", ["5m", "15m"])
@pytest.mark.parametrize("micros,selected", [(0, True), (1, False)])
def test_freshness_370_seconds_inclusive_and_next_microsecond_excluded(tf, micros, selected):
    inputs = OfflineInputs(frames={"5m": None, "15m": None})
    inputs.frames[tf] = history(tf)
    result = inputs.find(T + pd.Timedelta(seconds=370, microseconds=micros))
    assert (result is not None) is selected
    if selected:
        assert result[0].confirmed_at == T


def test_nearest_eligible_level_and_one_event_per_episode():
    # One vector sweeps both eligible anchors in the same episode. Only the
    # anchor nearest the confirming close survives the real detector's dedup.
    inputs = OfflineInputs(frames={"5m": history(), "15m": None},
                           levels=[("PSY-LO", 100.), ("YDAY-LO", 100.5), ("UP", 112.)])
    event, _ = inputs.find()
    assert (event.level_name, event.level_price, event.confirmed_at) == (
        "YDAY-LO", 100.5, T)
    assert len(inputs.detections[0][3]) == 1
    assert event.event_id == "OANDA:XAUUSD|לונג|2026-09-09T02:45:00+00:00"


def test_newest_refused_plan_is_selected_and_only_winner_is_priced(monkeypatch):
    inputs = OfflineInputs(frames={"5m": history(confirmed=T - pd.Timedelta(minutes=5)),
                                    "15m": history("15m", short=True)},
                           levels=[("PSY-LO", 100.), ("UP", 112.)])
    sidecar = producer()
    real = module("trading_system.tree_replay._vendor.reversal_pricing").build_plan
    priced = []

    def record(event, levels, frame):
        plan = real(event, levels, frame)
        priced.append((event.timeframe, plan))
        return plan

    monkeypatch.setattr(sidecar, "build_plan", record)
    event, plan = inputs.find()
    assert (event.timeframe, event.direction) == ("15m", "שורט")
    assert plan.targets == []
    assert plan.refusal == "אין רמה שמשלמת על הסטופ"
    assert plan.tradeable is False
    assert [tf for tf, _ in priced] == ["15m"]
    # Independent real older-only evaluation proves there was a paying choice.
    older = OfflineInputs(frames={"5m": inputs.frames["5m"], "15m": None}, levels=inputs.levels)
    _, older_plan = older.find()
    assert (older_plan.entry, older_plan.stop, older_plan.targets, older_plan.refusal) == (
        100., 93., [("UP", 112.)], None)
    assert older_plan.tradeable is True


@pytest.mark.parametrize("rev_dir,cand_dir,same_symbol,refused,candidate_refused,want", [
    ("לונג", "שורט", True, False, False, True),
    ("שורט", "לונג", True, False, False, True),
    ("לונג", "לונג", True, False, False, False),
    ("לונג", "שורט", False, False, False, False),
    ("לונג", "שורט", True, True, False, False),
    ("לונג", "שורט", True, False, True, True),
    ("", "שורט", True, False, False, False),
    ("לונג", "", True, False, False, False),
    (None, "שורט", True, False, False, False),
    ("לונג", None, True, False, False, False),
])
def test_conflicts_uses_reversal_tradeability_symbol_and_nonempty_opposite_directions(
        rev_dir, cand_dir, same_symbol, refused, candidate_refused, want):
    Plan = module("trading_system.tree_replay._vendor.pricing").Plan
    reversal = Plan(SYMBOL, 101., "reversal", rev_dir, 100., 93., [("UP", 112.)],
                    refusal="refused" if refused else None)
    candidate = Plan(SYMBOL if same_symbol else "OTHER", 99., "trend", cand_dir,
                     100., 107., [("DOWN", 88.)], refusal="refused" if candidate_refused else None)
    assert producer().conflicts(reversal, candidate) is want


@pytest.mark.parametrize("which", ["reversal", "candidate", "both"])
def test_conflicts_missing_plan_is_false(which):
    Plan = module("trading_system.tree_replay._vendor.pricing").Plan
    reversal = Plan(SYMBOL, 101., "reversal", "לונג", 100., 93., [("UP", 112.)])
    candidate = Plan(SYMBOL, 99., "trend", "שורט", 100., 107., [("DOWN", 88.)])
    assert producer().conflicts(None if which != "candidate" else reversal,
                                None if which != "reversal" else candidate) is False


def relocated(tmp_path):
    audit()  # Assert missing implementation before trying to copy it (RED).
    root, source = tmp_path / "project", tmp_path / "source"
    for directory in ("configs/trees", "trading_system/tree_replay/_vendor"):
        shutil.copytree(ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tools").mkdir()
    for name in ("reversal_producer", "levelmap", "range", "pricing", "reversal", "ema", "correction"):
        filename = f"check_{name}_source_parity.py"
        shutil.copyfile(ROOT / "tools" / filename, root / "tools" / filename)
    for filename in ("levelmap.py", "sessions.py", "tr.py", "basis.py", "quarters.py",
                     "tradeplan.py", "level_reversal.py", "indicators.py", "features.py", "auction.py"):
        target = source / "chartdesk" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / "chartdesk" / filename, target)
    return root, source


def run_audit(root, source=None, *, env_source=None):
    command = [sys.executable, "-B", str(root / "tools/check_reversal_producer_source_parity.py")]
    if source is not None:
        command += ["--source-root", str(source)]
    env = dict(os.environ)
    env.pop("TR_CHARTDESK_SOURCE_ROOT", None)
    if env_source is not None:
        env["TR_CHARTDESK_SOURCE_ROOT"] = str(env_source)
    run = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    assert run.returncode in (0, 2), run.stdout + run.stderr
    report = json.loads(run.stdout)
    assert run.returncode == (0 if report["subset_verified"] else 2)
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    return report


def blocked(report, reason):
    assert report["status"] == "BLOCKED"
    assert report["subset_verified"] is False
    assert report["source_subset_verified"] is False
    assert any(reason in item for item in report["blockers"]), report


def mutate(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_complete_pinned_producer_and_inherited_graph_verify():
    report = audit().check_source_parity(SOURCE)
    assert report["status"] == "VERIFIED"
    assert report["subset_verified"] is True
    assert report["source_subset_verified"] is True
    assert report["blockers"] == []
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    graph = report["dependency_audits"]["levelmap"]
    assert graph["subset_verified"] is True
    assert set(graph["dependency_audits"]) == {"pricing", "ema", "range", "correction"}


@pytest.mark.parametrize("old,new", [
    ("decision_time, source", "decision_time=None, source"),
    ("now = _utc(decision_time)", "now = _utc(pd.Timestamp.now(tz='UTC'))"),
    ("basis = source", "basis = map_source"),
    ("levelmap = map_source", "levelmap = source"),
    ("detect_frame = detector", "detect_frame = None"),
    ('getattr(level_corr, "unverified", False)', 'getattr(level_corr, "unverified", True)'),
    ('getattr(corr, "source", "") == "none"', 'False'),
    ('("5m", "15m")', '("15m", "5m")'),
    ('fetch_corrected(symbol, tf, 10)', 'fetch_corrected(symbol, tf, 9)'),
    ('max_age_s=LIVE_MAX_AGE_S[tf]', 'max_age_s=369.0'),
    ('row[0].timeframe == "5m"', 'row[0].timeframe == "15m"'),
    ('reverse=True', 'reverse=False'),
    ('except Exception:', 'except ValueError:'),
    ('and reversal.tradeable', 'and candidate.tradeable'),
    ('import pandas as pd\nfrom .level_reversal', 'import os\nimport pandas as pd\nfrom .level_reversal'),
    ('from __future__ import annotations\nimport pandas as pd',
     'import pandas as pd\nfrom __future__ import annotations'),
])
def test_vendor_signature_clock_bindings_guards_requests_freshness_selection_cannot_drift(tmp_path, old, new):
    root, source = relocated(tmp_path)
    mutate(root / VENDOR, old, new)
    blocked(run_audit(root, source), "VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("extra", ['\nraise RuntimeError("never execute vendor")\n',
                                   '\nfind_at = None\n', '\n"extra statement"\n',
                                   '\nimport pandas as pd\n'])
def test_full_ordered_module_rejects_extra_statements_without_executing_them(tmp_path, extra):
    root, source = relocated(tmp_path)
    path = root / VENDOR
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    blocked(run_audit(root, source), "VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("old,new", [
    ('def find(symbol: str, *, now=None):', 'def find(symbol: str, *, now=0):'),
    ('now = _utc(pd.Timestamp.now(tz="UTC") if now is None else now)', 'now = _utc(now)'),
    ('now = _utc(pd.Timestamp.now(tz="UTC") if now is None else now)',
     'changed_now = _utc(pd.Timestamp.now(tz="UTC") if now is None else now)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    source = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    map_source = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    detector = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    decision_time = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    basis = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    levelmap = None\n    levels, level_corr = levelmap.build(symbol)'),
    ('    levels, level_corr = levelmap.build(symbol)', '    detect_frame = None\n    levels, level_corr = levelmap.build(symbol)'),
])
def test_source_transformation_proves_signature_clock_and_binding_preconditions(old, new):
    checker = audit()
    text = (SOURCE / "chartdesk/level_reversal.py").read_text(encoding="utf-8")
    prefix, marker, tail = text.partition("def find(")
    assert marker and old in marker + tail
    mutated = prefix + (marker + tail).replace(old, new, 1)
    with pytest.raises(ValueError, match="SOURCE_"):
        checker._expected_module(mutated)


@pytest.mark.parametrize("change", ["commit", "blob", "symbols", "imports", "extra", "zero", "ready"])
def test_manifest_cannot_redefine_independent_audit_contract(tmp_path, change):
    root, source = relocated(tmp_path)
    path = root / MANIFEST
    value = json.loads(path.read_text(encoding="utf-8"))
    if change == "commit":
        value["commit"] = "0" * 40
    elif change == "blob":
        value["files"][0]["git_blob_sha1"] = "0" * 40
    elif change == "symbols":
        value["files"][0]["symbols"].reverse()
    elif change == "imports":
        value["files"][0]["allowed_imports"] += "\nimport os"
    elif change == "extra":
        value["allow_extra"] = True
    else:
        value["ready_for_replay"] = 0 if change == "zero" else True
    path.write_text(json.dumps(value), encoding="utf-8")
    blocked(run_audit(root, source), "CONTRACT_MISMATCH")


@pytest.mark.parametrize("change", ["commit", "duplicate", "missing"])
def test_exactly_one_pinned_chartdesk_baseline_required(tmp_path, change):
    root, source = relocated(tmp_path)
    path = root / "configs/trees/existing-alerts-baseline.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    row = next(row for row in value["repositories"] if row["name"] == "chart-desk")
    if change == "commit":
        row["commit"] = "0" * 40
    elif change == "duplicate":
        value["repositories"].append(row.copy())
    else:
        value["repositories"].remove(row)
    path.write_text(json.dumps(value), encoding="utf-8")
    blocked(run_audit(root, source), "BASELINE_COMMIT_MISMATCH")


def test_source_blob_mutation_is_blocked_without_execution(tmp_path):
    root, source = relocated(tmp_path)
    path = source / "chartdesk/level_reversal.py"
    path.write_text(path.read_text(encoding="utf-8") + '\nraise RuntimeError("never execute source")\n', encoding="utf-8")
    blocked(run_audit(root, source), "SOURCE_BLOB_MISMATCH")


@pytest.mark.parametrize("filename,old,new", [
    ("level_reversal.py", '"5m": 370.0', '"5m": 371.0'),
    ("reversal_pricing.py", "0.15 * atr", "0.16 * atr"),
    ("pricing.py", "MIN_RR = 1.2", "MIN_RR = 1.1"),
    ("levelmap_build.py", "basis.broker_shape_ok(corr, 20)", "basis.broker_shape_ok(corr, 0)"),
    ("indicators.py", "2.0 / (length + 1.0)", "1.0 / (length + 1.0)"),
    ("ranges.py", "ar = float(rng.mean())", "ar = float(rng.max())"),
    ("correction.py", "age_days >= days", "age_days > days"),
])
def test_inherited_calculation_drift_blocks_producer(tmp_path, filename, old, new):
    root, source = relocated(tmp_path)
    mutate(root / "trading_system/tree_replay/_vendor" / filename, old, new)
    blocked(run_audit(root, source), "DEPENDENCY_AUDIT_FAILED:levelmap")


def test_map_manifest_is_independently_sealed(tmp_path):
    root, source = relocated(tmp_path)
    path = root / "configs/trees/levelmap-source-contracts.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["ready_for_training"] = 0
    path.write_text(json.dumps(value), encoding="utf-8")
    blocked(run_audit(root, source), "DEPENDENCY_CONTRACT_MISMATCH:levelmap")


@pytest.mark.parametrize("field,value", [("subset_verified", 1), ("source_subset_verified", 1),
                                        ("blockers", ["failed"]), ("ready_for_replay", 0),
                                        ("ready_for_training", 0)])
def test_dependency_report_requires_literal_booleans_and_empty_blockers(tmp_path, field, value):
    root, source = relocated(tmp_path)
    # Only the isolated audit tool is replaced; no detector/pricer outputs are
    # mocked. This tests the protocol boundary against a malformed audit report.
    report = dict(subset_verified=True, source_subset_verified=True, blockers=[],
                  ready_for_replay=False, ready_for_training=False)
    report[field] = value
    (root / "tools/check_levelmap_source_parity.py").write_text(
        f"def check_source_parity(source_root):\n    return {report!r}\n", encoding="utf-8")
    blocked(run_audit(root, source), "DEPENDENCY_AUDIT_FAILED:levelmap")


@pytest.mark.parametrize("target", [VENDOR, MANIFEST, "configs/trees/levelmap-source-contracts.json",
                                     "tools/check_levelmap_source_parity.py"])
@pytest.mark.parametrize("bad", ["missing", "malformed"])
def test_missing_or_malformed_inputs_are_blocked_reports(tmp_path, target, bad):
    root, source = relocated(tmp_path)
    path = root / target
    if bad == "missing":
        path.unlink()
    else:
        path.write_text("{", encoding="utf-8")
    blocked(run_audit(root, source), "UNREADABLE")


def test_cli_source_root_precedence_and_missing_root(tmp_path):
    root, source = relocated(tmp_path)
    assert run_audit(root, source, env_source=tmp_path / "absent")["subset_verified"] is True
    assert run_audit(root, env_source=source)["subset_verified"] is True
    blocked(run_audit(root, env_source=tmp_path / "absent"), "SOURCE_UNREADABLE")


def test_runtime_clock_wrappers_are_outside_source_formula_audit(tmp_path):
    root, source = relocated(tmp_path)
    for name in ("periods.py", "frames.py", "levelmap.py"):
        (root / "trading_system/tree_replay" / name).write_text(
            'raise RuntimeError("runtime wrapper must not be imported by source audit")\n', encoding="utf-8")
    assert run_audit(root, source)["subset_verified"] is True

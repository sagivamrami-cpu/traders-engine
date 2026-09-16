"""Causal bars -> original matrix -> original tracker, with no score stubs."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.corrections import CorrectionEvidence
from trading_system.tree_replay.frames import FrameSpec
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
SYMBOL = "OANDA:XAUUSD"
STEPS = {"5m": timedelta(minutes=5), "15m": timedelta(minutes=15),
         "30m": timedelta(minutes=30), "1h": timedelta(hours=1), "4h": timedelta(hours=4)}
KEYS = (("4h", 240), ("1h", 240), ("30m", 90), ("15m", 55), ("5m", 55), ("15m", 5))


def api():
    name = "trading_system.tree_replay.admission_frames"
    assert importlib.util.find_spec(name) is not None, "causal admission frame provider missing"
    return importlib.import_module(name)


def request(tf="5m", days=55, *, price=100.0, rising=False, base=None, n=120):
    module = api()
    base = base or tf
    step = STEPS[base]
    start = T-n*step
    bars = []
    for i in range(n):
        at = start+i*step
        p = price+i if rising else price
        bars.append(ClosedBar(instrument=SYMBOL, timeframe=base, opened_at=at,
            closed_at=at+step, available_at=at+step, open=p, high=p+2,
            low=p-2, close=p, volume=1, source="synthetic"))
    schedule = SessionSchedule(instrument=SYMBOL, calendar_id=f"calendar-{tf}-{days}",
        version="v1", source="synthetic", available_at=start, coverage_start=start,
        coverage_end=T+timedelta(days=2),
        intervals=(SessionInterval(opened_at=start, closed_at=T+timedelta(days=2)),))
    frame = FrameSpec(frame_id=f"admission-{tf}-{days}", instrument=SYMBOL,
        timeframe=tf, base_timeframe=base, history_start=start, available_at=start,
        source="synthetic", version="v1", bars=tuple(bars), session_schedule=schedule,
        max_age_seconds=3600, grid_anchor=start)
    corr = CorrectionEvidence(evidence_id=frame.frame_id+"-c", frame_id=frame.frame_id,
        instrument=SYMBOL, version="v1", observed_at=T, available_at=T,
        provenance="synthetic", offset=0, source="tv_daily", confidence="exact", note="test")
    return module.AdmissionFrameRequest(timeframe=tf, lookback_days=days, frame=frame,
        correction=corr, max_correction_age_seconds=60)


def source(requests=None, **changes):
    return api().AdmissionFrameSource(**(dict(instrument=SYMBOL, decision_time=T,
        requests=tuple(request(tf, days) for tf, days in KEYS) if requests is None else requests) | changes))


def test_original_matrix_values_and_request_order_on_real_causal_frames():
    s = source()
    views = s.read_symbol(SYMBOL)
    assert list(views) == ["4h", "1h", "15m", "5m"]
    assert [(r["timeframe"], r["lookback_days"]) for r in s.fetch_trace] == [
        ("4h", 240), ("1h", 240), ("15m", 55), ("5m", 55)]
    for tf, view in views.items():
        # Characterized from audited original source before this provider:
        # constant prices yield VWAP NaN -> source short100, not a probability.
        assert (view.close, view.atr, view.net) == (100., 4., -41.25)
        assert [(r.tool, r.direction, r.strength) for r in view.reads] == [
            ("tr", 0, 20), ("supertrend", -1, 90), ("vwap", -1, 100), ("structure", 0, 0)]
        assert view.bar_ts == (T-STEPS[tf]).timestamp()
        assert view.basis_note is None
    assert [r["fetch_index"] for r in s.matrix_trace] == [0, 1, 2, 3]
    assert all(r["status"] == "AVAILABLE" for r in s.matrix_trace)


@pytest.mark.parametrize("tf,days", KEYS)
def test_all_request_keys_fetch_actual_supplied_depth_without_trimming(tf, days):
    s = source((request(tf, days),))
    frame, corr = s.fetch_corrected(SYMBOL, tf, days)
    assert len(frame) == 120 and frame.iloc[-1].close == 100
    assert corr.source == "tv_daily"
    assert s.fetch_trace[0]["frame"]["row_count"] == 120


def test_exact_lifecycle_m15_three_day_frame_is_accepted_and_fetched():
    s = source((request("15m", 3),))
    frame, corr = s.fetch_corrected(SYMBOL, "15m", 3)
    assert len(frame) == 120 and frame.iloc[-1].close == 100
    assert corr.source == "tv_daily"
    assert s.fetch_trace[0]["frame"]["row_count"] == 120


def test_distinct_m15_histories_and_nonconstant_calculation():
    s = source((request("15m", 55, rising=True), request("15m", 5, price=110)))
    view = s.read_symbol(SYMBOL, ("15m",))["15m"]
    other, _ = s.fetch_corrected(SYMBOL, "15m", 5)
    assert view.close == 219 and view.net > 0
    assert next(r for r in view.reads if r.tool == "tr").direction == 1
    assert other.iloc[-1].close == 110
    assert [(r["timeframe"], r["lookback_days"]) for r in s.fetch_trace] == [("15m", 55), ("15m", 5)]


def test_history_older_than_requested_days_is_not_trimmed():
    req = request("15m", 5, n=600)
    frame, _ = source((req,)).fetch_corrected(SYMBOL, "15m", 5)
    assert len(frame) == 600
    assert frame.index[0] == pd.Timestamp("2026-09-03T10:00:00Z")
    assert frame.index[0] < T-timedelta(days=5)


def test_missing_first_frame_aborts_matrix_and_records_failure():
    s = source((request("1h", 240),))
    with pytest.raises(Exception, match="REQUEST_MISSING"):
        s.read_symbol(SYMBOL, ("4h", "1h"))
    assert [r["timeframe"] for r in s.fetch_trace] == ["4h"]
    assert s.matrix_trace[0]["status"] == "BLOCKED"
    assert s.matrix_trace[0]["blocker"] == "REQUEST_MISSING"


@pytest.mark.parametrize("case,blocker", [
    ("missing", "CORRECTION_MISSING"), ("future", "CORRECTION_FUTURE_OBSERVATION"),
    ("late", "CORRECTION_UNAVAILABLE"), ("stale", "CORRECTION_STALE")])
def test_correction_availability_is_not_source_quality(case, blocker):
    req = request()
    if case == "missing":
        req = replace(req, correction=None)
    elif case == "future":
        req = replace(req, correction=replace(req.correction,
            observed_at=T+timedelta(microseconds=1), available_at=T+timedelta(microseconds=1)))
    elif case == "late":
        req = replace(req, correction=replace(req.correction, available_at=T+timedelta(microseconds=1)))
    else:
        req = replace(req, correction=replace(req.correction, observed_at=T-timedelta(seconds=61)))
    s = source((req,))
    with pytest.raises(Exception, match=blocker):
        s.read_symbol(SYMBOL, ("5m",))
    assert s.fetch_trace[0]["blocker"] == blocker
    assert s.matrix_trace[0]["blocker"] == blocker


@pytest.mark.parametrize("origin,confidence,note", [
    ("none", "unknown", "⚠ OANDA:XAUUSD: test"),
    ("none", "n/a", "⚠ OANDA:XAUUSD: test"),
    ("mt5_broker", "exact", "✅ OANDA:XAUUSD: test")])
def test_assessed_unverified_and_source_none_reach_original_calculation(origin, confidence, note):
    req = request()
    req = replace(req, correction=replace(req.correction, source=origin, confidence=confidence))
    s = source((req,))
    view = s.read_symbol(SYMBOL, ("5m",))["5m"]
    assert view.net == -41.25 and view.basis_note == note
    assert s.fetch_trace[0]["correction"]["status"] == "ASSESSED"


def test_returned_frames_views_and_repeated_fetches_do_not_share_mutations():
    s = source((request(),))
    frame, corr = s.fetch_corrected(SYMBOL, "5m", 55)
    frame.iloc[-1, frame.columns.get_loc("close")] = 999
    corr.note = "mutated"
    view = s.read_symbol(SYMBOL, ("5m",))["5m"]
    view.reads[0].strength = 999
    next_view = s.read_symbol(SYMBOL, ("5m",))["5m"]
    assert next_view.close == 100 and next_view.net == -41.25
    assert next_view.reads[0].strength == 20
    assert len(s.fetch_trace) == 3 and len(s.matrix_trace) == 2


@pytest.mark.parametrize("kind", ["missing_bar", "calendar"])
def test_incomplete_supplied_history_is_traced_not_filled(kind):
    req = request()
    if kind == "missing_bar":
        req = replace(req, frame=replace(req.frame, bars=req.frame.bars[:10]+req.frame.bars[11:]))
    else:
        req = replace(req, frame=replace(req.frame, session_schedule=replace(
            req.frame.session_schedule, coverage_end=T-timedelta(microseconds=1),
            intervals=(SessionInterval(opened_at=req.frame.history_start,
                                       closed_at=T-timedelta(minutes=5)),))))
    s = source((req,))
    with pytest.raises(Exception):
        s.read_symbol(SYMBOL, ("5m",))
    assert s.fetch_trace[0]["status"] == "BLOCKED"
    assert s.matrix_trace[0]["status"] == "BLOCKED"
    assert s.fetch_trace[0]["blocker"]


def test_known_forming_target_row_and_delayed_base_publication_use_actual_T():
    req = request("15m", 55, base="5m", n=360)
    extra = replace(req.frame.bars[-1], opened_at=T, closed_at=T+STEPS["5m"],
        available_at=T+STEPS["5m"]+timedelta(seconds=1), open=100, high=107, low=99, close=106)
    req = replace(req, frame=replace(req.frame, bars=req.frame.bars+(extra,)),
                  max_correction_age_seconds=3600)
    before = source((req,), decision_time=T+STEPS["5m"])
    with pytest.raises(Exception):
        before.read_symbol(SYMBOL, ("15m",))
    assert before.fetch_trace[0]["status"] == "BLOCKED"
    after = source((req,), decision_time=extra.available_at)
    view = after.read_symbol(SYMBOL, ("15m",))["15m"]
    assert view.close == 106 and view.bar_ts == T.timestamp()
    evidence = after.fetch_trace[0]["frame"]
    assert evidence["last_row"]["state"] == "FORMING"
    assert evidence["observed_at"] == "2026-09-09T16:05:00Z"
    assert evidence["available_at"] == "2026-09-09T16:05:01Z"


def test_future_bars_and_correction_values_cannot_change_earlier_readings():
    req = request()
    future = replace(req.frame.bars[-1], opened_at=T, closed_at=T+STEPS["5m"],
        available_at=T+STEPS["5m"], open=900, high=950, low=800, close=900)
    augmented = replace(req, frame=replace(req.frame, bars=req.frame.bars+(future,)))
    left, right = source((req,)), source((augmented,))
    assert left.read_symbol(SYMBOL, ("5m",)) == right.read_symbol(SYMBOL, ("5m",))
    assert left.fetch_trace == right.fetch_trace
    for offset in (10, 900):
        unavailable = replace(req, correction=replace(req.correction, offset=offset,
            available_at=T+timedelta(seconds=1)))
        s = source((unavailable,))
        with pytest.raises(Exception, match="CORRECTION_UNAVAILABLE"):
            s.read_symbol(SYMBOL, ("5m",))
        assert s.fetch_trace[0]["correction"]["evidence"] is None


@pytest.mark.parametrize("bad", ["key", "bool_days", "age", "timeframe", "frame", "correction", "instrument"])
def test_request_validation_is_native_and_exact(bad):
    req = request()
    changes = {"key": {"lookback_days": 240}, "bool_days": {"lookback_days": True},
        "age": {"max_correction_age_seconds": True}, "timeframe": {"timeframe": "1h"},
        "frame": {"frame": object()}, "correction": {"correction": object()},
        "instrument": {"correction": replace(req.correction, instrument="BINANCE:BTCUSDT")}}[bad]
    with pytest.raises(ValueError):
        replace(req, **changes)
    with pytest.raises(FrozenInstanceError):
        req.lookback_days = 240


@pytest.mark.parametrize("bad", ["gc", "alias", "naive", "precision", "list", "duplicate", "frame_id", "record_type"])
def test_source_validation_precedes_lazy_fetch(bad):
    req = request()
    changes = {"gc": {"instrument": "COMEX:GC"}, "alias": {"instrument": "XAUUSD"},
        "naive": {"decision_time": T.replace(tzinfo=None)},
        "precision": {"decision_time": pd.Timestamp(T)+pd.Timedelta(nanoseconds=1)},
        "list": {"requests": [req]}, "duplicate": {"requests": (req, req)},
        "record_type": {"requests": (req.frame,)}}
    if bad == "frame_id":
        other = request("15m", 55)
        other = replace(other, frame=replace(other.frame, frame_id=req.frame.frame_id),
            correction=replace(other.correction, frame_id=req.frame.frame_id))
        changes[bad] = {"requests": (req, other)}
    with pytest.raises(ValueError):
        source((req,), **changes[bad]) if "requests" not in changes[bad] else source(**changes[bad])


def test_invalid_source_method_requests_remain_traced():
    s = source((request(),))
    with pytest.raises(ValueError):
        s.fetch_corrected("BINANCE:BTCUSDT", "5m", 55)
    assert s.fetch_trace[-1]["status"] == "BLOCKED"
    with pytest.raises(Exception):
        s.read_symbol(SYMBOL, ("2h", "5m"))
    assert s.matrix_trace[-1]["status"] == "BLOCKED"
    assert len(s.fetch_trace) == 1


class TrackerPorts:
    def __init__(self, frames, rows=None):
        self.frames = frames
        self.rows = rows or {}

    def read_symbol(self, symbol, tfs):
        return self.frames.read_symbol(symbol, tfs)

    def fetch_corrected(self, symbol, tf, days):
        return self.frames.fetch_corrected(symbol, tf, days)

    def now_epoch(self):
        return T.timestamp()

    def load(self):
        return deepcopy(self.rows)


def test_original_tracker_bias_thesis_and_post_stop_use_actual_frames():
    s = source()
    ports = TrackerPorts(s, {"stopped": dict(symbol=SYMBOL, direction="שורט",
        state="STOPPED", ts=(T-timedelta(hours=3)).timestamp(), stop=97)})
    tracker = TrackerAdmission(ports)
    assert tracker._higher_bias(SYMBOL) == {"4h": -41.25, "1h": -41.25}
    assert tracker._thesis_baseline(SYMBOL, "לונג") == "broken"
    assert tracker._thesis_baseline(SYMBOL, "שורט") == "held"
    start = len(s.fetch_trace)
    assert tracker.blocked_after_stop(SYMBOL, "שורט") is None
    assert [(r["timeframe"], r["lookback_days"]) for r in s.fetch_trace[start:]] == [
        ("4h", 240), ("1h", 240), ("15m", 5)]
    ports.rows["stopped"]["stop"] = 99
    assert "ממתינים לשינוי מבנה" in tracker.blocked_after_stop(SYMBOL, "שורט")


def test_tracker_catch_does_not_erase_matrix_calculation_error(monkeypatch):
    from trading_system.tree_replay._vendor import admission_matrix
    s = source()
    def explode(*args, **kwargs):
        raise ArithmeticError("synthetic matrix failure")
    monkeypatch.setattr(admission_matrix, "read_frame", explode)
    assert TrackerAdmission(TrackerPorts(s))._higher_bias(SYMBOL) is None
    assert s.matrix_trace == [dict(timeframe="4h", fetch_index=0, status="BLOCKED",
        blocker="MATRIX_CALCULATION_ERROR", exception_type="ArithmeticError")]
    assert [r["timeframe"] for r in s.fetch_trace] == ["4h"]


def test_actual_selected_plan_records_with_causal_matrix_at_the_same_decision():
    from test_reversal_handoff import inputs, DetachedRecordPorts
    from trading_system.tree_replay.reversal_producer import _evaluate_reversal_asof
    args = inputs()
    decision = args["decision_time"]
    requests = []
    for tf, days in KEYS:
        req = request(tf, days)
        requests.append(replace(req,
            frame=replace(req.frame, max_age_seconds=14400),
            correction=replace(req.correction, observed_at=decision, available_at=decision)))
    frames = source(tuple(requests), decision_time=decision)

    class CausalRecordPorts(DetachedRecordPorts):
        def read_symbol(self, symbol, tfs):
            return frames.read_symbol(symbol, tfs)

    evaluation = _evaluate_reversal_asof(**args)
    before = deepcopy(evaluation.report)
    ports = CausalRecordPorts()
    assert TrackerAdmission(ports).record(evaluation.selected_plan) is True
    row = next(iter(ports.rows.values()))
    assert (row["entry"], row["stop"], row["kind"]) == (100., 93., "reversal")
    assert row["targets"][0][1] == 112.
    assert row["bias_at_send"] == {"4h": -41.25, "1h": -41.25}
    assert row["thesis_state"] == "broken"
    assert row["state"] == "OPEN" and row["revalidation_verified"] is False
    assert row["ts"] == decision.timestamp()
    assert [(r["timeframe"], r["lookback_days"]) for r in frames.fetch_trace] == [
        ("4h", 240), ("1h", 240), ("4h", 240), ("1h", 240),
        ("30m", 90), ("15m", 55), ("5m", 55)]
    assert all(pd.Timestamp(r["frame"]["observed_at"]) <= decision for r in frames.fetch_trace)
    assert evaluation.report == before and not before["ready_for_training"]

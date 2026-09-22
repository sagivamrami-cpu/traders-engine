"""Actual selected objects -> private handoff -> real offline tracker record.

Golden hashes captured BEFORE refactoring on Python 3.13.5, pandas 2.3.3,
NumPy 2.2.6, pytest 8.3.3. Expectations are literals, not a second evaluator.
Only synthetic input fixtures are shared; find/detection/pricing stay real.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from trading_system.tree_replay import reversal_producer as adapter
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
from test_reversal_producer import SYMBOL, T, history, maps, reversal


TARGETS = [
    ("ADR-HI/ADR50-HI/RD-HI/YDAY-HI/D2-HI/D3-HI/D4-HI", 112.0),
    ("Q-QUARTER", 125.0),
    ("Q-HALF", 150.0),
]
# Hand checked: DAY-OPEN reclaim from above, red M5 vector at 13:50,
# confirmation [open=99, high=102, low=99, close=101] at 13:55 -> 14:00.
REASONS = [
    "רמה: DAY-OPEN 100.00",
    "וקטור: PVSRA אדום על 5m",
    "הגעה מלמעלה וסגירה חוזרת דרך הרמה",
    "טריגר: נר אישור לאחר ספיגה",
]
GOLDENS = [
    ("accepted", "PRODUCER_SELECTED_UNADMITTED",
     "reversal-decision:ee71d09cd6f493c3b3337a1c3361339b2f92616e6b85348cf46ebe32f4acfac2",
     "2bcb79936f6b7c697b0419b43807bb42262be89ea8ded8e13c88baf966aa03dd"),
    ("refused", "PRODUCER_SELECTED_UNADMITTED",
     "reversal-decision:f4108f2ac91b7702835503dacff83d03fa6c9e764f38bf5703fb74f74413ab80",
     "80dc43f9309b7530fb473951e1c8fcb42c62513835ae0fdd66ed28cc1a16084c"),
    ("quiet", "NO_CANDIDATE",
     "reversal-decision:f65b52bd4a10b7682db738a912178e9b1cdf9df9abf479116d98c297fc076b02",
     "063c2e66fe5492d391ec797e9103828ee991aedb75b97f6ea3858b7e5f86c208"),
    ("unavailable_daily", "BLOCKED",
     "reversal-decision:210e7c0472032da134d4013685b21b25a6deca4bf210f349f3f2a26015db1413",
     "f2b37afdfd76254b0402b2c2509dc11b4940665bc1ea0753d78393eebdbc2ee7"),
]


def inputs(case="accepted"):
    ms = maps()
    rs = (reversal(), reversal("15m", short=True))
    instrument = SYMBOL
    if case == "refused":
        req = ms[0]
        ms = (replace(req, frame=replace(req.frame, bars=tuple(
            replace(b, high=110, low=90) for b in req.frame.bars))),)
        rs = (reversal(confirmed=T-timedelta(minutes=5)), reversal("15m", short=True))
    elif case == "quiet":
        quiet = []
        for tf in ("5m", "15m"):
            data = history(tf, confirmed=pd.Timestamp(T))
            data.iloc[:] = [103., 108., 98., 102., 100.]
            quiet.append(reversal(tf, rows=data))
        rs = tuple(quiet)
    elif case == "unavailable_daily":
        ms = ()
    elif case == "unavailable_producer":
        rs = (replace(reversal(), correction=None),)
    elif case == "unsupported":
        instrument, ms, rs = "COMEX:GC", (), ()
    elif case == "source_error":
        req = rs[0]
        rs = (replace(req, frame=replace(req.frame, bars=tuple(
            replace(b, volume=1e308) for b in req.frame.bars))), rs[1])
    elif case != "accepted":
        raise AssertionError(case)
    return dict(snapshot_id="test", instrument=instrument, decision_time=T,
                map_requests=ms, reversal_requests=rs)


def capture_find(monkeypatch):
    original = adapter.reversal_producer.find_at
    pairs = []

    def spy(*args, **kwargs):
        pair = original(*args, **kwargs)
        pairs.append(pair)
        return pair

    monkeypatch.setattr(adapter.reversal_producer, "find_at", spy)
    return pairs


def test_handoff_retains_single_actual_selection_and_original_geometry(monkeypatch):
    evaluate = adapter._evaluate_reversal_asof
    pairs = capture_find(monkeypatch)
    result = evaluate(**inputs())
    assert len(pairs) == 1
    assert result.selected_event is pairs[0][0]
    assert result.selected_plan is pairs[0][1]
    event, plan = result.selected_event, result.selected_plan
    assert result.report["status"] == "PRODUCER_SELECTED_UNADMITTED"
    assert (plan.symbol, plan.close, plan.kind, plan.direction, plan.style) == (
        SYMBOL, 101.0, "reversal", "לונג", "scalp")
    assert (plan.entry, plan.stop, plan.targets, plan.reasons, plan.obstacles) == (
        100.0, 93.0, TARGETS, REASONS, [])
    assert plan.tradeable is True and plan.born_open is None
    assert (event.timeframe, event.level_name, event.pattern, event.close) == (
        "5m", "DAY-OPEN", "two_bar_reclaim", 101.0)
    assert event.confirmed_at == pd.Timestamp("2026-09-09T14:00:00Z")
    assert event.confirmation_open_time == pd.Timestamp("2026-09-09T13:55:00Z")
    assert event.vector_open_time == pd.Timestamp("2026-09-09T13:50:00Z")
    assert event.event_id == "OANDA:XAUUSD|לונג|2026-09-09T13:45:00+00:00"
    with pytest.raises(FrozenInstanceError):
        result.selected_plan = None


@pytest.mark.parametrize("case,status,decision_id,digest", GOLDENS)
def test_private_public_reports_preserve_pre_refactor_hashes(case, status, decision_id, digest):
    evaluate = adapter._evaluate_reversal_asof
    result = evaluate(**inputs(case))
    public = adapter.find_reversal_asof(**inputs(case))
    assert result.report == public
    assert (public["status"], public["decision_id"], public["evaluation_sha256"]) == (
        status, decision_id, digest)
    assert public["calculation"]["pandas_version"] == "2.3.3"
    assert public["calculation"]["numpy_version"] == "2.2.6"
    assert public["schema_version"] == public["calculation_version"] == "tree-reversal-producer-asof-v1"
    assert not public["tradeable"] and not public["ready_for_replay"] and not public["ready_for_training"]


def test_newest_refused_original_plan_is_retained_over_older_paying_m5(monkeypatch):
    evaluate = adapter._evaluate_reversal_asof
    pairs = capture_find(monkeypatch)
    args = inputs("refused")
    result = evaluate(**args)
    assert len(pairs) == 1
    assert result.selected_event is pairs[0][0] and result.selected_plan is pairs[0][1]
    event, plan = result.selected_event, result.selected_plan
    assert (event.timeframe, event.confirmed_at, plan.close, plan.direction, plan.style) == (
        "15m", pd.Timestamp("2026-09-09T14:00:00Z"), 99.0, "שורט", "intraday")
    assert (plan.entry, plan.stop, plan.targets) == (100.0, 109.5, [("Q-QUARTER", 75.0)])
    assert plan.obstacles == [("ADR-LO/ADR50-LO/RD-LO/YDAY-LO/D2-LO/D3-LO/D4-LO", 90.0)]
    assert plan.refusal == (
        "יעד ראשון רחוק: 2.63R מעבר ל-2R, רמה אחת בדרך "
        "(ADR-LO/ADR50-LO/RD-LO/YDAY-LO/D2-LO/D3-LO/D4-LO 90.00)")
    assert not plan.tradeable and plan.born_open is None
    assert result.report["selected"]["pricing_status"] == "PRICE_REFUSED"
    older = evaluate(**{**args, "reversal_requests": args["reversal_requests"][:1]})
    assert older.selected_event.timeframe == "5m"
    assert older.selected_plan.tradeable is True


@pytest.mark.parametrize("case,status,blocker", [
    ("quiet", "NO_CANDIDATE", None),
    ("unavailable_daily", "BLOCKED", "REQUIRED_DAILY_INPUT_UNAVAILABLE"),
    ("unavailable_producer", "NO_SELECTION_INPUTS_UNAVAILABLE", None),
    ("unsupported", "BLOCKED", "PRODUCER_UNSUPPORTED_INSTRUMENT"),
    ("source_error", "BLOCKED", "PRODUCER_CALCULATION_ERROR"),
])
def test_nonselection_and_source_errors_retain_neither_object(case, status, blocker):
    evaluate = adapter._evaluate_reversal_asof
    result = evaluate(**inputs(case))
    assert (result.report["status"], result.report["blocker"]) == (status, blocker)
    assert result.report["selected"] is None
    assert result.selected_event is None and result.selected_plan is None


@pytest.mark.parametrize("path", ["_source_plan", "_pricing_snapshot"])
def test_late_pricing_serialization_failure_discards_real_selection(monkeypatch, path):
    evaluate = adapter._evaluate_reversal_asof
    pairs = capture_find(monkeypatch)
    original = getattr(adapter, path)

    def fail_after_serializing(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected late " + path + " serialization failure")

    monkeypatch.setattr(adapter, path, fail_after_serializing)
    result = evaluate(**inputs())
    assert len(pairs) == 1 and pairs[0][1].entry == 100.0
    assert pairs[0][1].close == 101.0 and pairs[0][1].kind == "reversal"
    assert (result.report["status"], result.report["blocker"]) == (
        "BLOCKED", "PRODUCER_CALCULATION_ERROR")
    assert result.report["diagnostic"] == {
        "stage": "pricing_serialization", "exception_type": "RuntimeError"}
    assert result.report["selected"] is None
    assert result.selected_event is None and result.selected_plan is None


@pytest.mark.parametrize("bad", ["snapshot", "naive_time", "submicrosecond", "list",
                              "duplicate", "instrument", "wrong_type"])
def test_private_evaluator_preserves_raised_input_validation(bad):
    evaluate = adapter._evaluate_reversal_asof
    args = inputs()
    if bad == "snapshot":
        args["snapshot_id"] = " "
    elif bad == "naive_time":
        args["decision_time"] = T.replace(tzinfo=None)
    elif bad == "submicrosecond":
        args["decision_time"] = pd.Timestamp(T) + pd.Timedelta(nanoseconds=1)
    elif bad == "list":
        args["reversal_requests"] = list(args["reversal_requests"])
    elif bad == "duplicate":
        args["reversal_requests"] = (reversal(), reversal())
    elif bad == "instrument":
        args["instrument"] = "COMEX:GC"
    else:
        args["map_requests"] = (reversal(),)
    with pytest.raises(ValueError) as private_error:
        evaluate(**args)
    with pytest.raises(ValueError) as public_error:
        adapter.find_reversal_asof(**args)
    assert type(private_error.value) is type(public_error.value)
    assert str(private_error.value) == str(public_error.value)


class DetachedRecordPorts:
    """Known empty state/quote and explicit synthetic matrix at T; no I/O."""

    def __init__(self):
        self.rows = {}

    def load(self):
        return deepcopy(self.rows)

    def save(self, rows):
        self.rows = deepcopy(rows)

    def now_epoch(self):
        return T.timestamp()

    @contextmanager
    def locked(self):
        yield

    def quote_payload(self):
        return {}

    def read_symbol(self, symbol, tfs):
        assert symbol == SYMBOL
        nets = {"4h": 10.0, "1h": 20.0, "30m": 5.0, "15m": 5.0, "5m": 5.0}
        return {tf: SimpleNamespace(net=nets[tf], bar_ts=T.timestamp()) for tf in tfs}


def test_actual_selected_plan_records_original_source_fields_without_changing_report(monkeypatch):
    evaluate = adapter._evaluate_reversal_asof
    pairs = capture_find(monkeypatch)
    ports = DetachedRecordPorts()
    result = evaluate(**inputs())
    assert ports.rows == {} and result.selected_plan.born_open is None
    before = deepcopy(result.report)
    assert TrackerAdmission(ports).record(result.selected_plan, variant="handoff-test") is True
    assert len(pairs) == 1 and result.selected_plan is pairs[0][1]
    assert len(ports.rows) == 1
    row = next(iter(ports.rows.values()))
    assert (row["entry"], row["stop"], row["kind"], row["direction"], row["style"]) == (
        100.0, 93.0, "reversal", "לונג", "scalp")
    assert row["targets"] == [
        ["ADR-HI/ADR50-HI/RD-HI/YDAY-HI/D2-HI/D3-HI/D4-HI", 112.0],
        ["Q-QUARTER", 125.0], ["Q-HALF", 150.0]]
    assert row["reasons"] == REASONS and row["obstacles"] == []
    # Close 101 is inside [98,102]; known empty quotes defer to build close.
    assert result.selected_plan.born_open is True
    assert row["state"] == "OPEN" and row["born_in_zone"] is True
    assert row["revalidation_verified"] is False
    assert row["fill_verification_reason"] == "born_open_not_broker_verified"
    assert row["ts"] == row["filled_ts"] == row["progress_ts"] == T.timestamp()
    assert row["bias_at_send"] == {"4h": 10.0, "1h": 20.0}
    assert row["thesis_state"] == "held"
    assert result.report == before
    assert not result.report["tradeable"] and not result.report["ready_for_replay"]
    assert not result.report["ready_for_training"]
    # A consumer's nested mutation cannot leak back into the retained Plan.
    row["targets"][0][1] = -1
    row["reasons"].append("consumer annotation")
    assert result.selected_plan.targets == TARGETS and result.selected_plan.reasons == REASONS


@pytest.mark.parametrize("case", ["accepted", "refused"])
def test_report_nested_lists_are_detached_from_mutable_selected_plan(case):
    evaluate = adapter._evaluate_reversal_asof
    result = evaluate(**inputs(case))
    plan = result.selected_plan
    before = deepcopy(result.report)
    plan.targets[0] = ("downstream", -1)
    plan.obstacles.append(("downstream obstacle", -2))
    plan.reasons.append("downstream reason")
    plan.warnings.append("downstream warning")
    assert result.report == before
    plan_before = deepcopy(plan)
    selected = result.report["selected"]
    selected["source_plan"]["targets"][0]["price"] = -3
    selected["source_plan"]["reasons"].append("report annotation")
    selected["source_plan"]["warnings"].clear()
    if case == "refused":
        selected["source_plan"]["obstacles"][0]["price"] = -4
    assert plan == plan_before
    assert result.report["candidates"] == before["candidates"]


def test_repeated_evaluations_own_independent_plans_events_and_reports():
    evaluate = adapter._evaluate_reversal_asof
    args = inputs()
    first, second = evaluate(**args), evaluate(**args)
    assert first.selected_plan is not second.selected_plan
    assert first.selected_event is not second.selected_event
    second_plan, second_report = deepcopy(second.selected_plan), deepcopy(second.report)
    first.selected_plan.born_open = True
    first.selected_plan.cooldown_release = {"reasons": ["downstream"]}
    first.selected_plan.entry_quality = {"labels": ["shadow"]}
    first.selected_plan.consumer_note = "test-only"
    for field in ("targets", "obstacles", "reasons", "warnings", "not_drawn", "entry_labels"):
        getattr(first.selected_plan, field).append("downstream mutation")
    first.report["selected"]["source_plan"]["targets"][0]["price"] = -1
    assert second.selected_plan == second_plan and not hasattr(second.selected_plan, "consumer_note")
    assert second.report == second_report
    assert evaluate(**args).report == second_report

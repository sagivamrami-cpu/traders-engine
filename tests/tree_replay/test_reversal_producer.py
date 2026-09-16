"""Real typed calendars/bars/corrections -> original map/find/detector/pricer.

Each scenario targets a wrong clock, gate, selection, evidence or boundary.
Only input seeds are shared with other tests; no source calculation is mocked.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import json

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.corrections import CorrectionEvidence
from trading_system.tree_replay.frames import FrameSpec
from trading_system.tree_replay.levelmap import MapFrameRequest
from test_levelmap import T, SYMBOL, daily, request as map_request
from test_reversal_producer_source import history


def adapter():
    name = "trading_system.tree_replay.reversal_producer"
    assert importlib.util.find_spec(name) is not None, "Task3 typed producer is missing"
    return importlib.import_module(name)


def maps():
    frame = daily(16)
    frame = replace(frame, bars=tuple(replace(b, open=100, high=112, low=88, close=100)
                                      for b in frame.bars))
    return (map_request(frame, 400),)


def reversal(tf="5m", *, confirmed=T, short=False, trailing=False, rows=None):
    data = history(tf, confirmed=pd.Timestamp(confirmed), short=short, trailing=trailing)
    if rows is not None:
        data = rows
    step = timedelta(minutes=int(tf[:-1]))
    start, end = data.index[0].to_pydatetime(), (data.index[-1]+step).to_pydatetime()
    bars = tuple(ClosedBar(instrument=SYMBOL, timeframe=tf,
        opened_at=at.to_pydatetime(), closed_at=(at+step).to_pydatetime(),
        available_at=(at+step).to_pydatetime(), source="synthetic",
        **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")})
        for at, row in data.iterrows())
    schedule = SessionSchedule(instrument=SYMBOL, calendar_id="synthetic-reversal",
        version="v1", source="synthetic", available_at=start, coverage_start=start,
        coverage_end=T+timedelta(days=1),
        intervals=(SessionInterval(opened_at=start, closed_at=end),))
    frame = FrameSpec(frame_id="producer-"+tf, instrument=SYMBOL, timeframe=tf,
        base_timeframe=tf, history_start=start, available_at=start, source="synthetic",
        version="v1", bars=bars, session_schedule=schedule, max_age_seconds=7200,
        grid_anchor=start)
    correction = CorrectionEvidence(evidence_id=frame.frame_id+"-correction",
        frame_id=frame.frame_id, instrument=SYMBOL, version="v1", observed_at=start,
        available_at=start, provenance="synthetic", offset=0, source="tv_daily",
        confidence="high", note="supplied synthetic history")
    return adapter().ReversalFrameRequest(frame=frame, correction=correction,
                                          max_correction_age_seconds=86400)


def find(requests=None, *, decision=T, map_inputs=None, **kwargs):
    return adapter().find_reversal_asof(snapshot_id="test", instrument=SYMBOL,
        decision_time=decision, map_requests=maps() if map_inputs is None else map_inputs,
        reversal_requests=(reversal(), reversal("15m", short=True)) if requests is None else requests,
        **kwargs)


def test_real_equal_confirmation_opposite_setups_select_m5_and_price_only_winner():
    result = find()
    assert result["status"] == "PRODUCER_SELECTED_UNADMITTED"
    assert [(c["timeframe"], c["direction"]) for c in result["candidates"]] == [
        ("5m", "LONG"), ("15m", "SHORT")]
    chosen = result["selected"]
    assert (chosen["timeframe"], chosen["level_price"]) == ("5m", 100.)
    assert chosen["source_plan"]["entry"] == 100.
    assert chosen["source_plan"]["stop"] == 93.
    # Pinned XAU zone is entry +/-2; the stop is five below its lower edge.
    assert chosen["source_plan"]["entry_zone"] == {"low": 98., "high": 102.}
    assert chosen["source_plan"]["targets"][0] == {
        "name": "ADR-HI/ADR50-HI/RD-HI/YDAY-HI/D2-HI/D3-HI/D4-HI", "price": 112.}
    assert chosen["pricing_status"] == "PRICE_ACCEPTED_UNADMITTED"
    assert result["candidates"][1]["source_plan"] is None
    assert [(r["timeframe"], r["lookback_days"]) for r in result["fetch_trace"]] == [
        ("5m", 10), ("15m", 10)]
    assert [(r["timeframe"], r["max_age_s"], r["decision_time"]) for r in result["detection_trace"]] == [
        ("5m", 370., "2026-09-09T14:00:00Z"), ("15m", 370., "2026-09-09T14:00:00Z")]


def test_newer_m15_wins_over_fresh_m5():
    result = find((reversal(confirmed=T-timedelta(minutes=5)), reversal("15m", short=True)))
    assert (result["selected"]["timeframe"], result["selected"]["direction"]) == ("15m", "SHORT")
    assert len(result["candidates"]) == 2


def test_older_confirmation_keeps_event_clock_and_observes_current_map_at_T():
    result = find((reversal(confirmed=T-timedelta(minutes=5), trailing=True),))
    selected = result["selected"]
    assert selected["confirmed_at"] == "2026-09-09T13:55:00Z"
    assert selected["vector_open_time"] == "2026-09-09T13:45:00Z"
    assert result["map_report"]["level_snapshot"]["observed_at"] == "2026-09-09T14:00:00Z"
    for snapshot in (selected["snapshot"], selected["pricing_snapshot"]):
        assert all(v["observed_at"] == "2026-09-09T14:00:00Z" and
                   v["available_at"] == "2026-09-09T14:00:00Z"
                   for v in snapshot["provenance"].values())
    features = selected["snapshot"]["features"]
    assert features["reversal.vector_volume"] == 200.
    assert features["reversal.vector_prior_avg_volume_10"] == 100.
    assert features["reversal.vector_volume_ratio"] == 2.
    assert features["reversal.vector_spread_volume"] == 800.


@pytest.mark.parametrize("tf", ["5m", "15m"])
@pytest.mark.parametrize("micros,selected", [(0, True), (1, False)])
def test_age_370_seconds_inclusive_then_microsecond_rejects(tf, micros, selected):
    result = find((reversal(tf),), decision=T+timedelta(seconds=370, microseconds=micros))
    assert (result["selected"] is not None) is selected
    assert len(result["detection_trace"]) == 1


def test_between_close_and_T_publication_is_usable_only_when_published():
    req = reversal()
    publication = T+timedelta(seconds=23, microseconds=7)
    bars = req.frame.bars[:-1]+(replace(req.frame.bars[-1], available_at=publication),)
    req = replace(req, frame=replace(req.frame, bars=bars))
    before = find((req,), decision=publication-timedelta(microseconds=1))
    after = find((req,), decision=publication)
    assert before["status"] == "NO_SELECTION_INPUTS_UNAVAILABLE"
    assert before["fetch_trace"][0]["status"] == "BLOCKED"
    assert after["selected"]["confirmed_at"] == "2026-09-09T14:00:00Z"
    assert after["fetch_trace"][0]["frame"]["available_at"] == "2026-09-09T14:00:23.000007Z"


@pytest.mark.parametrize("source,confidence,passes", [
    ("tv_daily", "high", True), ("replay", "high", True), ("cash_hours", "low", True),
    ("none", "n/a", False), ("none", "unknown", False)])
@pytest.mark.parametrize("tf,other", [("5m", "15m"), ("15m", "5m")])
def test_actual_intraday_correction_gates_preserve_other_timeframe(source, confidence, passes, tf, other):
    req = reversal(tf)
    req = replace(req, correction=replace(req.correction, source=source, confidence=confidence))
    result = find((req, reversal(other)))
    assert len(result["candidates"]) == (2 if passes else 1)
    trace = next(r for r in result["fetch_trace"] if r["timeframe"] == tf)
    assert trace["producer_gate"]["passed"] is passes
    assert trace["producer_gate"]["source"] == source
    if not passes:
        assert result["selected"]["timeframe"] == other


@pytest.mark.parametrize("source,confidence,passes", [
    ("tv_daily", "high", True), ("replay", "high", True), ("cash_hours", "low", True),
    ("none", "n/a", True), ("none", "unknown", False)])
def test_actual_daily_gate_does_not_invent_blanket_source_none_veto(source, confidence, passes):
    req = maps()[0]
    req = replace(req, correction=replace(req.correction, source=source, confidence=confidence))
    result = find(map_inputs=(req,))
    assert (result["selected"] is not None) is passes
    if not passes:
        assert result["status"] == "NO_CANDIDATE"
        assert result["reason"] == "DAILY_CORRECTION_UNVERIFIED"
        assert result["fetch_trace"] == []


def test_required_daily_missing_blocks_and_keeps_original_report():
    result = find(map_inputs=())
    assert result["status"] == "BLOCKED"
    assert result["blocker"] == "REQUIRED_DAILY_INPUT_UNAVAILABLE"
    assert result["map_report"]["fetch_trace"][0]["blocker"] == "REQUEST_MISSING"
    assert result["fetch_trace"] == []


@pytest.mark.parametrize("why", ["missing", "future", "delayed", "stale"])
def test_unavailable_producer_corrections_are_not_negative_examples(why):
    req = reversal()
    changes = {"missing": None, "future": replace(req.correction, observed_at=T+timedelta(seconds=1),
        available_at=T+timedelta(seconds=1), note="FUTURE-SECRET"),
        "delayed": replace(req.correction, available_at=T+timedelta(seconds=1), note="FUTURE-SECRET"),
        "stale": replace(req.correction, observed_at=T-timedelta(days=2))}
    result = find((replace(req, correction=changes[why]),))
    assert result["status"] == "NO_SELECTION_INPUTS_UNAVAILABLE"
    assert result["selected"] is None and result["detection_trace"] == []
    assert "FUTURE-SECRET" not in json.dumps(result)


@pytest.mark.parametrize("mode,reason", [("quiet", "NO_CANDIDATE"), ("warmup", "WARMUP")])
def test_evaluated_quiet_and_warmup_are_distinct_from_unavailable(mode, reason):
    requests = []
    for tf in ("5m", "15m"):
        data = history(tf, confirmed=pd.Timestamp(T))
        data.iloc[:] = [103., 108., 98., 102., 100.]
        if mode == "warmup":
            data = data.iloc[-11:]
        requests.append(reversal(tf, rows=data))
    result = find(tuple(requests))
    assert result["status"] == "NO_CANDIDATE"
    assert [r["reason"] for r in result["detection_trace"]] == [reason, reason]


@pytest.mark.parametrize("volume,only_one", [(None, False), (None, True), (0., False)])
def test_missing_or_all_zero_volume_skips_only_affected_tf(volume, only_one):
    req = reversal()
    bars = tuple(replace(b, volume=volume) if not only_one or i == 3 else b
                 for i, b in enumerate(req.frame.bars))
    req = replace(req, frame=replace(req.frame, bars=bars))
    result = find((req, reversal("15m")))
    assert result["selected"]["timeframe"] == "15m"
    assert result["fetch_trace"][0]["blocker"] == "VOLUME_UNAVAILABLE"
    assert result["fetch_trace"][0]["status"] == "BLOCKED"


def test_numeric_overflow_cannot_masquerade_as_quiet_or_partial_success():
    req = reversal()
    req = replace(req, frame=replace(req.frame, bars=tuple(replace(b, volume=1e308) for b in req.frame.bars)))
    result = find((req, reversal("15m")))
    assert result["status"] == "BLOCKED"
    assert result["diagnostic"]["exception_type"] == "ValueError"
    assert result["diagnostic"]["stage"] == "detector_history"
    assert result["selected"] is None


def test_future_unused_payloads_request_order_and_output_mutation_do_not_change_evaluation():
    reqs = (reversal(), reversal("15m"))
    original = find(reqs)
    req = reqs[0]
    future = replace(req.frame.bars[-1], opened_at=T, closed_at=T+timedelta(minutes=5),
        available_at=T+timedelta(minutes=5), high=999999, volume=999999)
    changed = replace(req, frame=replace(req.frame, bars=req.frame.bars+(future,)))
    assert find((reqs[1], changed)) == original
    original["selected"]["snapshot"]["features"]["reversal.vector_volume"] = -1
    assert original["candidates"][0]["snapshot"]["features"]["reversal.vector_volume"] == 200.
    assert find(reqs)["selected"]["snapshot"]["features"]["reversal.vector_volume"] == 200.


def test_repeat_event_ids_group_consideration_but_decision_and_snapshot_ids_differ():
    requests = (reversal(), reversal("15m"))
    first = find(requests)
    assert first["candidates"][0]["source_event_id"] == first["candidates"][1]["source_event_id"]
    assert first["candidates"][0]["candidate_id"] != first["candidates"][1]["candidate_id"]
    next_time = find(requests, decision=T+timedelta(microseconds=1))
    assert first["selected"]["candidate_id"] == next_time["selected"]["candidate_id"]
    assert first["selected"]["source_event_id"] == next_time["selected"]["source_event_id"]
    assert first["decision_id"] != next_time["decision_id"]
    again = adapter().find_reversal_asof(snapshot_id="other", instrument=SYMBOL,
        decision_time=T, map_requests=maps(), reversal_requests=requests)
    assert first["decision_id"] != again["decision_id"]
    assert first["selected"]["candidate_id"] == again["selected"]["candidate_id"]


def test_hash_is_canonical_and_public_results_never_admit_send_or_label():
    result = find()
    assert result["schema_version"] == result["calculation_version"] == "tree-reversal-producer-asof-v1"
    assert result["source_commit"] == "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
    digest = result.pop("evaluation_sha256")
    assert digest == hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert not result["tradeable"] and not result["ready_for_replay"] and not result["ready_for_training"]
    assert all(not c["tradeable"] for c in result["candidates"])
    assert not {"send", "label", "outcome", "fill"}.intersection(result)
    assert result["missing_stages"] == ["outer_market_watch_admission", "tracker_episode_state",
        "cross_producer_arbitration", "execution_and_outcomes", "full_tree_dataset_training"]


@pytest.mark.parametrize("policy", [-1, True, 1., None])
def test_non_native_or_negative_correction_policy_raises(policy):
    req = reversal()
    with pytest.raises(ValueError):
        replace(req, max_correction_age_seconds=policy)


@pytest.mark.parametrize("kind", ["list", "wrong_type", "duplicate_tf", "duplicate_id", "cross_id",
                                  "instrument", "map_duplicate", "map_wrong_type"])
def test_structural_identity_validation_precedes_lazy_map_veto(kind):
    req = reversal()
    rs, ms = (req,), ()
    if kind == "list": rs = [req]
    if kind == "wrong_type": rs = (req.frame,)
    if kind == "duplicate_tf": rs = (req, req)
    if kind == "duplicate_id":
        other = reversal("15m")
        other = replace(other, frame=replace(other.frame, frame_id=req.frame.frame_id),
                        correction=replace(other.correction, frame_id=req.frame.frame_id))
        rs = (req, other)
    if kind == "cross_id":
        daily_req = maps()[0]
        ms = (replace(daily_req, frame=replace(daily_req.frame, frame_id=req.frame.frame_id),
                      correction=replace(daily_req.correction, frame_id=req.frame.frame_id)),)
    if kind == "instrument":
        # Exact instrument must be validated even when the required map is absent.
        with pytest.raises(ValueError):
            adapter().find_reversal_asof(snapshot_id="x", instrument="COMEX:GC", decision_time=T,
                                         map_requests=(), reversal_requests=rs)
        return
    if kind == "map_duplicate": ms = (maps()[0], maps()[0])
    if kind == "map_wrong_type": ms = (req,)
    with pytest.raises(ValueError):
        find(rs, map_inputs=ms)


def test_unsupported_exact_gc_blocks_without_source_pricing():
    result = adapter().find_reversal_asof(snapshot_id="gc", instrument="COMEX:GC",
        decision_time=T, map_requests=(), reversal_requests=())
    assert (result["status"], result["blocker"]) == ("BLOCKED", "PRODUCER_UNSUPPORTED_INSTRUMENT")
    assert result["selected"] is None and result["fetch_trace"] == []


@pytest.mark.parametrize("decision", [T.replace(tzinfo=None), pd.Timestamp(T)+pd.Timedelta(nanoseconds=1)])
def test_invalid_decision_precision_raises(decision):
    with pytest.raises(ValueError):
        find((), decision=decision, map_inputs=())


def test_frozen_request_rejects_wrong_correction_association():
    req = reversal()
    with pytest.raises(FrozenInstanceError):
        req.max_correction_age_seconds = 0
    with pytest.raises(ValueError):
        replace(req, correction=replace(req.correction, frame_id="other"))


def test_newest_refused_plan_stays_selected_despite_older_paying_plan():
    # Symmetric ten-point daily rails: M5 risks 7 and can pay at 110. M15
    # risks 9.5, so 90 is an obstacle before the far paying quarter at 75.
    req = maps()[0]
    req = replace(req, frame=replace(req.frame, bars=tuple(
        replace(b, high=110, low=90) for b in req.frame.bars)))
    older = reversal(confirmed=T-timedelta(minutes=5))
    result = find((older, reversal("15m", short=True)), map_inputs=(req,))
    assert result["status"] == "PRODUCER_SELECTED_UNADMITTED"
    chosen = result["selected"]
    assert (chosen["timeframe"], chosen["pricing_status"]) == ("15m", "PRICE_REFUSED")
    plan = chosen["source_plan"]
    assert (plan["entry"], plan["stop"]) == (100., 109.5)
    assert plan["targets"] == [{"name": "Q-QUARTER", "price": 75.}]
    assert plan["obstacles"] == [{
        "name": "ADR-LO/ADR50-LO/RD-LO/YDAY-LO/D2-LO/D3-LO/D4-LO", "price": 90.}]
    assert plan["refusal"] == (
        "יעד ראשון רחוק: 2.63R מעבר ל-2R, רמה אחת בדרך "
        "(ADR-LO/ADR50-LO/RD-LO/YDAY-LO/D2-LO/D3-LO/D4-LO 90.00)")
    assert not plan["source_tradeable"]
    assert result["candidates"][0]["source_plan"] is None
    assert find((older,), map_inputs=(req,))["selected"]["pricing_status"] == "PRICE_ACCEPTED_UNADMITTED"


def m15_with_forming_base(*, only_forming=False, volume=200.):
    req = reversal("15m", short=True)
    bars = tuple(replace(b, timeframe="5m", opened_at=b.opened_at+timedelta(minutes=i*5),
        closed_at=b.opened_at+timedelta(minutes=(i+1)*5),
        available_at=b.opened_at+timedelta(minutes=(i+1)*5), volume=b.volume/3)
        for b in req.frame.bars for i in range(3))
    extra = replace(bars[-1], opened_at=T, closed_at=T+timedelta(minutes=5),
        available_at=T+timedelta(minutes=5), open=102, high=102, low=98, close=101, volume=volume)
    start = T if only_forming else req.frame.history_start
    schedule = replace(req.frame.session_schedule, coverage_start=start,
        intervals=(SessionInterval(opened_at=start, closed_at=extra.closed_at),))
    frame = replace(req.frame, base_timeframe="5m", history_start=start, grid_anchor=start,
        bars=(extra,) if only_forming else bars+(extra,), session_schedule=schedule)
    return replace(req, frame=frame)


@pytest.mark.parametrize("volume", [200., None])
def test_forming_m15_never_confirms_and_its_missing_volume_does_not_veto_closed_history(volume):
    req = m15_with_forming_base(volume=volume)
    result = find((req,), decision=T+timedelta(minutes=5))
    chosen = result["selected"]
    assert (chosen["confirmed_at"], chosen["direction"]) == ("2026-09-09T14:00:00Z", "SHORT")
    trace = result["fetch_trace"][1]
    assert trace["frame"]["last_row"]["state"] == "FORMING"
    assert trace["closed_rows"] == 12
    assert len(result["candidates"]) == 1


def test_forming_only_target_is_evaluated_warmup_not_missing_volume():
    # Five completed base minutes cannot confirm a fifteen-minute target.
    req = m15_with_forming_base(only_forming=True)
    result = find((req,), decision=T+timedelta(minutes=5))
    assert len(result["detection_trace"]) == 1
    assert result["detection_trace"][0]["reason"] == "WARMUP"
    assert result["detection_trace"][0]["closed_rows"] == 0
    assert result["selected"] is None


def test_unused_map_fallback_and_future_prices_cannot_change_result_or_hash():
    from test_levelmap import inputs
    requests = inputs(16)
    original = find(map_inputs=requests)
    assert original["map_report"]["status"] == "BUILT_UNADMITTED"
    assert ("15m", 20) not in [(r["timeframe"], r["lookback_days"])
                               for r in original["map_report"]["fetch_trace"]]
    unused = requests[3]
    unused = replace(unused, max_correction_age_seconds=0,
        correction=replace(unused.correction, note="UNUSED-FALLBACK", offset=98765))
    changed = list(requests)
    changed[3] = unused
    for i, req in enumerate(changed):
        b = req.frame.bars[-1]
        future = replace(b, opened_at=T, closed_at=T+(b.closed_at-b.opened_at),
            available_at=T+(b.closed_at-b.opened_at), high=999999, volume=999999)
        changed[i] = replace(req, frame=replace(req.frame, bars=req.frame.bars+(future,)))
    assert find(map_inputs=tuple(reversed(changed))) == original


def test_missing_optional_map_inputs_retain_map_and_original_selection():
    result = find()
    assert result["map_report"]["status"] == "BUILT_UNADMITTED"
    assert any(r["blocker"] == "REQUEST_MISSING" for r in result["map_report"]["fetch_trace"][1:])
    assert result["status"] == "PRODUCER_SELECTED_UNADMITTED"
    assert result["selected"]["timeframe"] == "5m"


@pytest.mark.parametrize("which", ["daily", "producer"])
def test_future_correction_payload_changes_do_not_change_hash(which):
    req = maps()[0] if which == "daily" else reversal()
    future = replace(req.correction, observed_at=T+timedelta(seconds=1),
        available_at=T+timedelta(seconds=1), note="HIDDEN-ONE", offset=123456)
    first = replace(req, correction=future)
    second = replace(req, correction=replace(future, note="HIDDEN-TWO", offset=654321))
    a = find(map_inputs=(first,)) if which == "daily" else find((first,))
    b = find(map_inputs=(second,)) if which == "daily" else find((second,))
    assert a == b
    assert "HIDDEN" not in json.dumps(a)


@pytest.mark.parametrize("mutation", ["bar", "calendar", "frame", "correction"])
def test_daily_publication_is_checked_at_actual_T_before_producer_runs(mutation):
    req = maps()[0]
    publication = T+timedelta(seconds=17, microseconds=3)
    if mutation == "bar":
        req = replace(req, frame=replace(req.frame, bars=req.frame.bars[:-1]+(
            replace(req.frame.bars[-1], available_at=publication),)))
    elif mutation == "calendar":
        req = replace(req, frame=replace(req.frame, session_schedule=replace(
            req.frame.session_schedule, available_at=publication)))
    elif mutation == "frame":
        req = replace(req, frame=replace(req.frame, available_at=publication))
    else:
        req = replace(req, correction=replace(req.correction, available_at=publication))
    before = find(map_inputs=(req,), decision=publication-timedelta(microseconds=1))
    after = find(map_inputs=(req,), decision=publication)
    assert before["status"] == "BLOCKED" and before["fetch_trace"] == []
    assert after["status"] == "PRODUCER_SELECTED_UNADMITTED"
    assert after["map_report"]["level_snapshot"]["observed_at"] == "2026-09-09T14:00:17.000003Z"


def test_map_numeric_failure_is_blocked_even_if_graph_catches_optional_fetch():
    from test_levelmap import intraday
    daily_req = maps()[0]
    optional = map_request(intraday("4h", 240, count=8), 240)
    assert find(map_inputs=(daily_req, optional))["status"] == "PRODUCER_SELECTED_UNADMITTED"
    # Each supplied one-hour volume is finite. Summing four of them into
    # the optional four-hour EMA frame overflows, inside a caught fetch.
    optional = replace(optional, frame=replace(optional.frame, bars=tuple(
        replace(b, volume=1e308) for b in optional.frame.bars)))
    result = find(map_inputs=(daily_req, optional))
    assert (result["status"], result["blocker"]) == ("BLOCKED", "FRAME_CALCULATION_ERROR")
    assert result["diagnostic"] == {
        "stage": "fetch", "exception_type": "ValueError", "timeframe": "4h", "lookback_days": 240}
    report = result["map_report"]
    assert report["diagnostic"] == result["diagnostic"]
    daily_fetch = report["fetch_trace"][0]
    assert (daily_fetch["timeframe"], daily_fetch["lookback_days"], daily_fetch["status"],
            daily_fetch["blocker"]) == ("1d", 400, "AVAILABLE", None)
    assert daily_fetch["correction"]["status"] == "ASSESSED"
    failed = next(r for r in report["fetch_trace"]
                  if (r["timeframe"], r["lookback_days"]) == ("4h", 240))
    assert (failed["frame_id"], failed["status"], failed["blocker"]) == (
        "4h-240", "BLOCKED", "FRAME_CALCULATION_ERROR")
    assert result["selected"] is None and result["fetch_trace"] == []


def test_required_daily_numeric_failure_is_a_source_build_error():
    # Daily range arithmetic overflows on finite inputs; source errors remain
    # typed diagnostics, never negative observations or admitted candidates.
    req = maps()[0]
    req = replace(req, frame=replace(req.frame, bars=tuple(
        replace(b, high=1e308, low=1.) for b in req.frame.bars)))
    result = find(map_inputs=(req,))
    assert (result["status"], result["blocker"]) == ("BLOCKED", "SOURCE_CALCULATION_ERROR")
    assert result["diagnostic"] == {"stage": "build", "exception_type": "FloatingPointError"}
    assert [(r["timeframe"], r["lookback_days"], r["status"])
            for r in result["map_report"]["fetch_trace"]] == [("1d", 400, "AVAILABLE")]
    assert result["selected"] is None


def test_old_detector_guard_and_default_feature_observation_remain_unchanged():
    from trading_system.tree_replay.levels import LevelSnapshot, NamedLevel
    from trading_system.tree_replay.reversal import detect_reversals_asof
    req = reversal(confirmed=T-timedelta(minutes=5))
    levels = LevelSnapshot(snapshot_id="current-map", instrument=SYMBOL, source="synthetic",
        version="v1", observed_at=T, available_at=T,
        levels=(NamedLevel(name="DAY-OPEN", price=100.),))
    params = dict(snapshot_id="old", instrument=SYMBOL, timeframe="5m", decision_time=T,
        history_start=req.frame.history_start, max_age_seconds=370, max_level_age_seconds=370)
    result = detect_reversals_asof(req.frame.bars, level_snapshot=levels, **params)
    assert result["blocker"] == "LEVELS_AFTER_CONFIRMATION"
    at = T-timedelta(minutes=5)
    result = detect_reversals_asof(req.frame.bars,
        level_snapshot=replace(levels, observed_at=at, available_at=at), **params)
    assert result["status"] == "DETECTED_UNPRICED"
    assert all(p["observed_at"] == "2026-09-09T13:55:00Z"
               for p in result["candidates"][0]["snapshot"]["provenance"].values())


@pytest.mark.parametrize("value", ["", " ", None, 1])
def test_invalid_snapshot_identity_raises(value):
    with pytest.raises(ValueError):
        adapter().find_reversal_asof(snapshot_id=value, instrument=SYMBOL,
            decision_time=T, map_requests=(), reversal_requests=())


@pytest.mark.parametrize("bad", ["frame", "correction", "request", "map_request"])
def test_exact_types_prevent_subclass_overrides_at_public_boundary(bad):
    req = reversal()
    ms, rs = (), (req,)
    if bad == "frame":
        class SubFrame(FrameSpec):
            pass
        with pytest.raises(ValueError):
            replace(req, frame=SubFrame(**{f: getattr(req.frame, f) for f in req.frame.__dataclass_fields__}))
        return
    if bad == "correction":
        class SubCorrection(CorrectionEvidence):
            pass
        with pytest.raises(ValueError):
            replace(req, correction=SubCorrection(**{f: getattr(req.correction, f)
                for f in req.correction.__dataclass_fields__}))
        return
    if bad == "request":
        class SubRequest(adapter().ReversalFrameRequest):
            pass
        rs = (SubRequest(frame=req.frame, correction=req.correction,
                         max_correction_age_seconds=86400),)
    else:
        class SubMap(MapFrameRequest):
            pass
        req = maps()[0]
        ms = (SubMap(**{f: getattr(req, f) for f in req.__dataclass_fields__}),)
    with pytest.raises(ValueError):
        find(rs, map_inputs=ms)


def test_real_pandas_target_close_overflow_records_fetch_error_before_source_can_skip():
    # A native microsecond target close is legal beyond pandas' ns range;
    # its source index and the five-minute observation are still in range.
    start = datetime(2262, 4, 11, 23, 40, tzinfo=timezone.utc)
    decision = start+timedelta(minutes=5)
    bar = ClosedBar(instrument=SYMBOL, timeframe="5m", opened_at=start, closed_at=decision,
        available_at=decision, open=100, high=102, low=98, close=101, volume=200, source="synthetic")
    schedule = SessionSchedule(instrument=SYMBOL, calendar_id="boundary", version="v1",
        source="synthetic", available_at=start, coverage_start=start, coverage_end=decision,
        intervals=(SessionInterval(opened_at=start, closed_at=decision),))
    frame = FrameSpec(frame_id="boundary", instrument=SYMBOL, timeframe="15m", base_timeframe="5m",
        history_start=start, available_at=start, source="synthetic", version="v1", bars=(bar,),
        session_schedule=schedule, max_age_seconds=0, grid_anchor=start)
    correction = replace(reversal().correction, frame_id="boundary", observed_at=start, available_at=start)
    req = adapter().ReversalFrameRequest(frame=frame, correction=correction, max_correction_age_seconds=300)
    source = adapter()._ProducerSource(SYMBOL, decision, (req,))
    with pytest.raises(OverflowError):
        source.fetch_corrected(SYMBOL, "15m", 10)
    assert source.fetch_trace[0]["status"] == "BLOCKED"
    assert source.error == {"stage": "detector_history", "exception_type": "OverflowError",
                            "timeframe": "15m", "lookback_days": 10}


def test_zero_correction_age_policy_accepts_only_same_instant():
    req = reversal()
    req = replace(req, max_correction_age_seconds=0,
        correction=replace(req.correction, observed_at=T, available_at=T))
    assert find((req,))["status"] == "PRODUCER_SELECTED_UNADMITTED"
    later = find((req,), decision=T+timedelta(microseconds=1))
    assert later["status"] == "NO_SELECTION_INPUTS_UNAVAILABLE"
    assert later["fetch_trace"][0]["blocker"] == "CORRECTION_STALE"

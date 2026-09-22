"""Real synthetic frame -> source graph -> detector/pricer integration.

Literal rails catch changed source ordering/gates; temporal mutations catch
future leakage, stale admission, eager fallback fetches and stale map clocks.
No calculation dependency is mocked.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import json

import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.corrections import CorrectionEvidence
from trading_system.tree_replay.frames import FrameSpec, LabeledDailyPeriod
from trading_system.tree_replay.levels import LevelSnapshot, NamedLevel
from trading_system.tree_replay.periods import DailyPeriod


T = datetime(2026, 9, 9, 14, tzinfo=timezone.utc)
SYMBOL = "OANDA:XAUUSD"


def adapter():
    name = "trading_system.tree_replay.levelmap"
    assert importlib.util.find_spec(name) is not None, "Task3 public adapter is missing"
    return importlib.import_module(name)


def bar(opened, tf="1h", row=(100, 110, 90, 100), minutes=60):
    closed = opened + timedelta(minutes=minutes)
    return ClosedBar(instrument=SYMBOL, timeframe=tf, opened_at=opened,
                     closed_at=closed, available_at=closed, open=row[0], high=row[1],
                     low=row[2], close=row[3], volume=100, source="synthetic")


def calendar(start, intervals):
    return SessionSchedule(instrument=SYMBOL, calendar_id="synthetic-hours",
                           version="v1", source="supplied-synthetic", available_at=start,
                           coverage_start=start, coverage_end=T+timedelta(days=2),
                           intervals=tuple(SessionInterval(opened_at=a, closed_at=b)
                                           for a, b in intervals))


def daily(count=220):
    # Explicit daily labels, with one scheduled hour per synthetic day. This
    # sparsity is the supplied calendar, not an inference about market hours.
    start = T.replace(hour=0)-timedelta(days=count-1)
    days = [start+timedelta(days=i) for i in range(count)]
    bars = tuple(bar(d+timedelta(hours=13), row=(100, 115, 95, 110)
                     if i == count-1 else (100, 110, 90, 100))
                 for i, d in enumerate(days))
    periods = tuple(LabeledDailyPeriod(source_index_at=d, period=DailyPeriod(
        instrument=SYMBOL, period_id=d.date().isoformat(), opened_at=d,
        closed_at=d+timedelta(days=1), available_at=start, source="synthetic", version="v1"))
        for d in days)
    return FrameSpec(frame_id="daily", instrument=SYMBOL, timeframe="1d", base_timeframe="1h",
                     history_start=start, available_at=start, source="synthetic", version="v1",
                     bars=bars, periods=periods, max_age_seconds=7200,
                     session_schedule=calendar(start, [(b.opened_at, b.closed_at) for b in bars]))


def intraday(tf, lookback, *, count=None, row=(100, 110, 90, 100)):
    base, minutes = ("5m", 5) if tf in ("5m", "15m") else ("1h", 60)
    count = count if count is not None else {"5m":84, "15m":768, "1h":64, "4h":1602}[tf]
    start = T-timedelta(minutes=count*minutes)
    bars = tuple(bar(start+timedelta(minutes=i*minutes), base, row, minutes) for i in range(count))
    if tf == "5m":
        bars = tuple(replace(b, open=103 if b.opened_at.hour == 7 and b.opened_at.minute == 0
                             else 107 if b.opened_at.hour == 13 and b.opened_at.minute == 30
                             else b.open) for b in bars)
    return FrameSpec(frame_id=f"{tf}-{lookback}", instrument=SYMBOL, timeframe=tf,
                     base_timeframe=base, history_start=start, available_at=start,
                     source="synthetic", version="v1", bars=bars, max_age_seconds=7200,
                     grid_anchor=start, session_schedule=calendar(start, [(start,T+timedelta(days=1))]))


def request(frame, lookback, **correction_changes):
    evidence = CorrectionEvidence(evidence_id=frame.frame_id+"-correction", frame_id=frame.frame_id,
        instrument=frame.instrument, version="v1", observed_at=T, available_at=T,
        provenance="supplied-synthetic", offset=0, source="tv_daily", confidence="high", note="fixture")
    return adapter().MapFrameRequest(timeframe=frame.timeframe, lookback_days=lookback,
        frame=frame, correction=replace(evidence, **correction_changes), max_correction_age_seconds=7200)


def inputs(count=220):
    return (request(daily(count),400), request(intraday("5m",3),3),
            request(intraday("1h",20,row=(100,150,80,100)),20),
            request(intraday("15m",20,row=(100,160,70,100)),20),
            request(intraday("1h",240,count=1600),240), request(intraday("4h",240),240))


def build(requests, decision=T, instrument=SYMBOL):
    return adapter().build_levelmap_asof(instrument=instrument, decision_time=decision, requests=requests)


def snapshot(result):
    data = dict(result["level_snapshot"])
    data["levels"] = tuple(NamedLevel(**v) for v in data["levels"])
    for key in ("observed_at", "available_at"):
        data[key] = datetime.fromisoformat(data[key].replace("Z", "+00:00"))
    return LevelSnapshot(**data)


def pairs(result):
    return [(v["name"], v["price"]) for v in result["levels"]]


def test_complete_source_families_prices_order_forming_state_and_false_readiness():
    result = build(inputs())
    assert result["status"] == "BUILT_UNADMITTED" and result["blocker"] is None
    assert pairs(result) == [
        ("ADR-HI",115), ("ADR-LO",95), ("AWR-HI",110), ("AWR-LO",95),
        ("RW-HI",110), ("RW-LO",95), ("AMR-HI",110), ("AMR-LO",95),
        ("ADR50-HI",110), ("ADR50-LO",90), ("AWR50-HI",110), ("AWR50-LO",90),
        ("AMR50-HI",110), ("AMR50-LO",90), ("RD-HI",115), ("RD-LO",95),
        ("YDAY-HI",110), ("YDAY-LO",90), ("YDAY-CLOSE",100),
        ("D2-HI",110), ("D2-LO",90), ("D3-HI",110), ("D3-LO",90),
        ("D4-HI",110), ("D4-LO",90), ("LWEEK-HI",110), ("LWEEK-LO",90),
        ("DAY-OPEN",100), ("WEEK-OPEN",100), ("LONDON-OPEN",103), ("NY-OPEN",107),
        ("PSY-HI",150), ("PSY-LO",80), ("EMA200-1h",pytest.approx(100)),
        ("EMA800-1h",pytest.approx(100)), ("CLOUD50-4h",pytest.approx(100)),
        ("EMA200-4h",pytest.approx(100)),
        ("Q-WHOLE",100), ("Q-QUARTER",125), ("Q-QUARTER",75), ("Q-HALF",150)]
    assert [v["kind"] for v in result["levels"]] == ["level"]*31+["psy"]*2+["ema"]*4+["quarter"]*4
    assert result["source_missing"] == []
    assert [(x["timeframe"],x["lookback_days"]) for x in result["fetch_trace"]] == [
        ("1d",400),("5m",3),("1h",20),("1h",240),("4h",240)]
    assert [(x["lookback_days"],x["broker_shape_ok"]) for x in result["shape_trace"]] == [(20,True),(7,True)]
    assert result["fetch_trace"][-1]["frame"]["last_row"]["state"] == "FORMING"
    assert result["fetch_trace"][-1]["frame"]["last_row"]["observed_at"] == "2026-09-09T14:00:00Z"
    assert not result["tradeable"] and not result["ready_for_replay"] and not result["ready_for_training"]
    assert result["level_correction"]["status"] == "ASSESSED"
    assert snapshot(result).observed_at == T
    assert not {"candidate", "fill", "label", "outcome"}.intersection(result)
    payload = dict(result)
    digest = payload.pop("evaluation_sha256")
    assert digest == hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":"), allow_nan=False).encode()).hexdigest()


def test_future_bar_and_unused_fallback_payloads_do_not_change_result():
    requests = inputs(16)
    first = build(requests)
    changed = []
    for req in requests:
        last = req.frame.bars[-1]
        step = last.closed_at-last.opened_at
        future = replace(last, opened_at=T, closed_at=T+step, available_at=T+step,
                         high=999999, low=1, volume=999999)
        changed.append(replace(req, frame=replace(req.frame, bars=req.frame.bars+(future,))))
    changed[3] = replace(changed[3], max_correction_age_seconds=0,
                         correction=replace(changed[3].correction, note="UNUSED",offset=999))
    assert build(tuple(changed)) == first
    assert build(tuple(reversed(requests))) == first


@pytest.mark.parametrize("why", ["missing", "bar_missing", "bar_delayed", "metadata", "correction_missing", "stale", "future", "delayed"])
def test_daily_unavailable_blocks_without_snapshot_or_future_payload(why):
    req = request(daily(16),400)
    if why == "missing":
        requests = ()
    else:
        if why in ("bar_missing", "bar_delayed"):
            bars = req.frame.bars[:-1]
            if why == "bar_delayed":
                bars += (replace(req.frame.bars[-1], available_at=T+timedelta(seconds=1)),)
            req = replace(req, frame=replace(req.frame, bars=bars))
        elif why == "metadata":
            req = replace(req, frame=replace(req.frame, available_at=T+timedelta(seconds=1)))
        elif why == "correction_missing":
            req = replace(req, correction=None)
        else:
            observed = T-timedelta(seconds=7201) if why == "stale" else T+timedelta(seconds=1) if why == "future" else T
            req = replace(req, correction=replace(req.correction, observed_at=observed,
                available_at=T+timedelta(seconds=1) if why != "stale" else T, note="SECRET-FUTURE", offset=987654))
        requests = (req,)
    result = build(requests)
    assert result["status"] == "BLOCKED" and result["blocker"] == "REQUIRED_DAILY_INPUT_UNAVAILABLE"
    assert result["levels"] == [] and result["level_snapshot"] is None
    assert len(result["fetch_trace"]) == 1 and result["fetch_trace"][0]["blocker"]
    assert result["level_correction"] is None
    assert "SECRET-FUTURE" not in json.dumps(result) and "987654" not in json.dumps(result)


def test_optional_unavailable_preserves_original_psy_exception_boundary_and_ema_omissions():
    requests = inputs(16)
    result = build((requests[0], requests[3], replace(requests[4], correction=None)))
    assert result["status"] == "BUILT_UNADMITTED"
    assert not any(v["kind"] in ("psy", "ema") for v in result["levels"])
    assert not any(x["timeframe"] == "15m" for x in result["fetch_trace"])
    assert len(result["source_missing"]) == 5  # AWR/RW/AMR warmup + both EMA fetches
    assert all(x["blocker"] for x in result["fetch_trace"][1:])


@pytest.mark.parametrize("source,confidence,rails,opens,psy", [
    ("tv_daily","high",True,True,True), ("replay","high",False,True,False),
    ("none","unknown",False,False,False), ("cash_hours","low",False,True,False)])
def test_correction_gates_are_asymmetric_not_blanket_admission(source,confidence,rails,opens,psy):
    requests = tuple(replace(r, correction=replace(r.correction,source=source,confidence=confidence)) for r in inputs(16))
    result = build(requests)
    names = {v["name"] for v in result["levels"]}
    assert result["status"] == "BUILT_UNADMITTED"
    assert ("ADR-HI" in names) is rails and ("RD-HI" in names) is rails
    assert ("LONDON-OPEN" in names) is opens and ("PSY-HI" in names) is psy
    assert {"ADR50-HI", "YDAY-HI", "EMA200-1h"} <= names
    assert result["level_correction"]["unverified"] is (source == "none")


def test_psy_fallback_is_used_only_after_assessed_hourly_shape_rejection():
    requests = list(inputs(16))
    requests[2] = replace(requests[2],correction=replace(requests[2].correction,source="replay"))
    result = build(tuple(requests))
    assert ("PSY-HI",160) in pairs(result) and ("PSY-LO",70) in pairs(result)
    assert [x["lookback_days"] for x in result["shape_trace"]] == [20,7,7]
    assert result["shape_trace"][1]["broker_shape_ok"] is False
    assert result["shape_trace"][2]["broker_shape_ok"] is True


def test_actual_splice_lookback_is_separate_from_zero_day_fetch_preflight():
    req = request(daily(16),400,source="tv_spliced",tv_from=T-timedelta(days=20)+timedelta(microseconds=1))
    result = build((req,))
    assert result["fetch_trace"][0]["correction"]["broker_shape_ok"] is True
    assert result["fetch_trace"][0]["correction"]["lookback_days"] == 0
    assert result["shape_trace"][0]["lookback_days"] == 20
    assert result["shape_trace"][0]["broker_shape_ok"] is False
    assert ("ADR-HI",115) not in pairs(result)


def test_map_clock_and_dependency_publication_are_separate():
    req = request(daily(16),400,source="tv_spliced",tv_from=T-timedelta(days=20)+timedelta(minutes=30))
    later = T+timedelta(hours=1)
    first, second = build((req,)), build((req,),decision=later)
    assert ("ADR-HI",115) not in pairs(first) and ("ADR-HI",115) in pairs(second)
    assert snapshot(second).observed_at == snapshot(second).available_at == later
    assert second["fetch_trace"][0]["frame"]["observed_at"] == "2026-09-09T14:00:00Z"
    assert second["fetch_trace"][0]["frame"]["available_at"] == "2026-09-09T14:00:00Z"


def test_stable_ids_and_no_mutation_when_another_family_disappears():
    requests = inputs(16)
    before = repr(requests)
    first = build(requests)
    reduced = build((replace(requests[0],correction=replace(requests[0].correction,source="replay")),)+requests[1:])
    ids = {(v.name,v.price):v.level_id for v in snapshot(first).levels}
    assert all(ids[(v.name,v.price)] == v.level_id for v in snapshot(reduced).levels)
    quarters = [v for v in snapshot(first).levels if v.name == "Q-QUARTER"]
    assert len(quarters) == 2 and len({v.level_id for v in quarters}) == 2
    first["levels"][0]["price"] = 999
    first["fetch_trace"][0]["correction"]["evidence"]["note"] = "changed"
    assert build(requests) != first and repr(requests) == before
    with pytest.raises(FrozenInstanceError):
        requests[0].lookback_days = 1


@pytest.mark.parametrize("field,value", [("lookback_days",True),("lookback_days",400.0),("lookback_days",1),
    ("max_correction_age_seconds",True),("max_correction_age_seconds",-1),("max_correction_age_seconds",1.5),
    ("timeframe","4h"),("frame",{}),("correction",{})])
def test_request_rejects_unsupported_keys_types_and_policies(field,value):
    req = request(daily(16),400)
    with pytest.raises(ValueError):
        replace(req,**{field:value})


def test_identity_duplicates_tuple_types_and_decision_precision_rejected():
    req = request(daily(16),400)
    for requests in ([req], (object(),), (req,req)):
        with pytest.raises(ValueError):
            build(requests)
    other = request(intraday("1h",20),20)
    other_frame = replace(other.frame,frame_id=req.frame.frame_id)
    other = replace(other,frame=other_frame,correction=replace(other.correction,frame_id=other_frame.frame_id))
    with pytest.raises(ValueError):
        build((req,other))
    for change in (dict(instrument="CME:GC"), dict(frame_id="other")):
        with pytest.raises(ValueError):
            replace(req,correction=replace(req.correction,**change))
    for instrument in ("GC","CME:GC","oanda:XAUUSD"):
        with pytest.raises(ValueError):
            build((req,),instrument=instrument)
    with pytest.raises(ValueError):
        build((req,),decision=T.replace(tzinfo=None))


def test_nonpositive_original_source_level_blocks_entire_map_without_filtering():
    req = request(daily(16),400)
    # Valid positive OHLC can generate a negative projected lower rail.
    bars = tuple(replace(b,open=2,close=2,high=100,low=1) for b in req.frame.bars)
    result = build((replace(req,frame=replace(req.frame,bars=bars)),))
    assert result["status"] == "BLOCKED" and result["blocker"] == "INVALID_SOURCE_LEVEL"
    assert result["levels"] == [] and result["level_snapshot"] is None
    assert result["diagnostic"]["level_name"] == "ADR50-LO"


def test_actual_map_is_consumed_by_real_reversal_and_pricing_without_manual_levels():
    from test_pricing import fixture
    from trading_system.tree_replay.pricing import price_reversals_asof
    from trading_system.tree_replay.reversal import detect_reversals_asof
    result = build(inputs(16))
    bars,args = fixture()
    shift = T-bars[-1].closed_at
    bars = [replace(b,opened_at=b.opened_at+shift,closed_at=b.closed_at+shift,available_at=b.available_at+shift) for b in bars]
    args.update(decision_time=T,history_start=bars[0].opened_at,level_snapshot=snapshot(result))
    detected = detect_reversals_asof(bars,**args)
    assert detected["status"] == "DETECTED_UNPRICED"
    assert all(c["level_price"] == pytest.approx(100) for c in detected["candidates"])
    priced = price_reversals_asof(bars,**args)
    assert priced["status"] == "PRICING_EVALUATED"
    assert priced["candidates"] and all(not c["tradeable"] for c in priced["candidates"])
    assert any(c["source_plan"]["entry"] == pytest.approx(100) and c["source_plan"]["stop"] == pytest.approx(93)
               for c in priced["candidates"])
    assert not priced["ready_for_replay"] and not priced["ready_for_training"]
    flat = [replace(b,open=200,high=201,low=199,close=200,volume=100) for b in bars]
    assert price_reversals_asof(flat,**args)["status"] == "NO_CANDIDATE"


@pytest.mark.parametrize("change,blocker", [
    ("missing_bar","HISTORY_GAP"), ("late_bar","HISTORY_GAP"),
    ("late_metadata","FRAME_METADATA_UNAVAILABLE"), ("stale_correction","CORRECTION_STALE")])
def test_optional_current_input_failures_are_traced_without_trying_psy_fallback(change,blocker):
    requests = list(inputs(16))
    req = requests[2]
    if change in ("missing_bar","late_bar"):
        bars = req.frame.bars[:-1]
        if change == "late_bar":
            bars += (replace(req.frame.bars[-1],available_at=T+timedelta(seconds=1)),)
        req = replace(req,frame=replace(req.frame,bars=bars))
    elif change == "late_metadata":
        req = replace(req,frame=replace(req.frame,available_at=T+timedelta(seconds=1)))
    else:
        req = replace(req,correction=replace(req.correction,observed_at=T-timedelta(seconds=7201)))
    requests[2] = req
    result = build(tuple(requests))
    assert result["status"] == "BUILT_UNADMITTED"
    assert result["fetch_trace"][2]["blocker"] == blocker
    assert not any(x["timeframe"] == "15m" for x in result["fetch_trace"])
    assert not any(x["kind"] == "psy" for x in result["levels"])
    assert ("EMA200-1h",pytest.approx(100)) in pairs(result)


def test_zero_correction_age_is_exact_and_unavailable_payload_changes_are_irrelevant():
    req = replace(request(daily(16),400),max_correction_age_seconds=0)
    assert build((req,))["status"] == "BUILT_UNADMITTED"
    stale = replace(req,correction=replace(req.correction,observed_at=T-timedelta(microseconds=1)))
    result = build((stale,))
    assert result["fetch_trace"][0]["blocker"] == "CORRECTION_STALE"
    assert build((replace(stale,correction=replace(stale.correction,offset=12345,note="unavailable")),)) == result


@pytest.mark.parametrize("source_symbol,rails,quarters", [
    ("CME:GC",False,False), ("BINANCE:BTCUSDT",True,True)])
def test_exact_source_instrument_survives_without_gc_alias(source_symbol,rails,quarters):
    req = request(daily(16),400,source="replay")
    # A positive BTC-scale price also keeps the original BTC quarter grid positive.
    bars = tuple(replace(b,instrument=source_symbol,open=b.open+75000,high=b.high+75000,
                         low=b.low+75000,close=b.close+75000) for b in req.frame.bars)
    frame = replace(req.frame,instrument=source_symbol,bars=bars,
        session_schedule=replace(req.frame.session_schedule,instrument=source_symbol),
        periods=tuple(replace(p,period=replace(p.period,instrument=source_symbol)) for p in req.frame.periods))
    req = replace(req,frame=frame,correction=replace(req.correction,instrument=source_symbol))
    result = build((req,),instrument=source_symbol)
    assert result["status"] == "BUILT_UNADMITTED"
    assert result["instrument"] == snapshot(result).instrument == source_symbol
    assert any(x["name"] == "ADR-HI" for x in result["levels"]) is rails
    assert any(x["kind"] == "quarter" for x in result["levels"]) is quarters


def test_source_numeric_overflow_cannot_leak_nonfinite_levels_or_hash():
    req = request(daily(16),400)
    bars = tuple(replace(b,open=1e308,high=1.7e308,low=1e307,close=1e308) for b in req.frame.bars)
    with pytest.warns(RuntimeWarning,match="overflow"):
        result = build((replace(req,frame=replace(req.frame,bars=bars)),))
    assert result["blocker"] == "INVALID_SOURCE_LEVEL"
    assert result["diagnostic"]["level_name"] == "ADR-HI"
    assert result["level_snapshot"] is None and result["levels"] == []
    json.dumps(result,allow_nan=False)


def test_uncaught_source_resample_error_blocks_map_with_diagnostic():
    req = request(daily(16),400)
    # Legal explicit source labels at pandas' representable edge: weekly
    # resampling must extend beyond it. Exercise the real exception boundary.
    periods = tuple(replace(p,source_index_at=datetime(2262,3,27,tzinfo=timezone.utc)+timedelta(days=i))
                    for i,p in enumerate(req.frame.periods))
    result = build((replace(req,frame=replace(req.frame,periods=periods)),))
    assert result["status"] == "BLOCKED" and result["blocker"] == "SOURCE_CALCULATION_ERROR"
    assert result["diagnostic"] == {"stage":"build","exception_type":"OutOfBoundsDatetime"}
    assert result["fetch_trace"][0]["status"] == "AVAILABLE"
    assert result["level_snapshot"] is None and result["levels"] == []

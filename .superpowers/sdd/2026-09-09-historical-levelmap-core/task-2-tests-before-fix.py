"""Historical frame regressions: real calendars/base bars and literal OHLC."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.periods import DailyPeriod


T = datetime(2020, 1, 3, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)
US = timedelta(microseconds=1)
SYMBOL = "OANDA:XAUUSD"


def api():
    name = "trading_system.tree_replay.frames"
    assert importlib.util.find_spec(name) is not None, "Missing assigned causal frame builder"
    return importlib.import_module(name)


def bar(start, i=0, **changes):
    return ClosedBar(**(dict(
        instrument=SYMBOL, timeframe="5m", opened_at=start, closed_at=start+STEP,
        available_at=start+STEP, open=100+i, high=102+i, low=99+i, close=101+i,
        volume=1, source="synthetic-price-evidence",
    ) | changes))


def schedule(start, end, intervals):
    return SessionSchedule(
        instrument=SYMBOL, calendar_id="synthetic-calendar", version="v1",
        coverage_start=start, coverage_end=end, available_at=start,
        source="synthetic calendar evidence", intervals=tuple(
            SessionInterval(opened_at=a, closed_at=b) for a, b in intervals),
    )


def daily():
    module = api()
    periods, bars, intervals = [], [], []
    for n in (-2, -1, 0):
        start = T+timedelta(days=n)
        period = DailyPeriod(instrument=SYMBOL, period_id=f"day{n}",
                             opened_at=start, closed_at=start+timedelta(days=1),
                             available_at=start, source="synthetic-day", version="v1")
        periods.append(module.LabeledDailyPeriod(period=period, source_index_at=start))
        intervals.append((start, start+3*STEP))
        for i in range(3):
            bars.append(bar(start+i*STEP, 0))
    bars[-3] = replace(bars[-3], open=100, high=110, low=95, close=108)
    bars[-2] = replace(bars[-2], open=108, high=115, low=100, close=110)
    bars[-1] = replace(bars[-1], open=110, high=1000, low=1, close=900)
    return module.FrameSpec(
        frame_id="daily-frame", instrument=SYMBOL, timeframe="1d", base_timeframe="5m",
        history_start=T-timedelta(days=2), available_at=T-timedelta(days=2),
        source="synthetic-frame-policy", version="v1", bars=tuple(bars),
        session_schedule=schedule(T-timedelta(days=2), T+timedelta(days=1), intervals),
        max_age_seconds=0, periods=tuple(periods),
    )


def intraday(n=7, timeframe="15m", start=T):
    module = api()
    return module.FrameSpec(
        frame_id=f"intraday-{timeframe}", instrument=SYMBOL, timeframe=timeframe,
        base_timeframe="5m", history_start=start, available_at=start,
        source="synthetic-grid-policy", version="v1",
        bars=tuple(bar(start+i*STEP, i) for i in range(n)),
        session_schedule=schedule(start, start+timedelta(days=1), [(start, start+n*STEP)]),
        max_age_seconds=0, grid_anchor=start,
    )


def build(spec, decision=None):
    return api().build_frame_asof(spec, decision_time=decision or T+2*STEP)


def test_daily_current_row_uses_known_prefix_not_final_day():
    result = build(daily())
    assert result["status"] == "AVAILABLE"
    assert [r["state"] for r in result["rows"]] == ["CLOSED", "CLOSED", "FORMING"]
    row = result["rows"][-1]
    assert [row[k] for k in ("open", "high", "low", "close", "volume")] == [100, 115, 95, 110, 2]
    assert row["observed_at"] == "2020-01-03T00:10:00Z"
    assert row["closed_at"] == "2020-01-04T00:00:00Z"
    assert result["ready_for_replay"] is False
    assert result["ready_for_training"] is False


def test_future_bar_and_period_extensions_do_not_change_selected_hash():
    original = daily()
    result = build(original)
    later = T+timedelta(days=1)
    period = api().LabeledDailyPeriod(period=DailyPeriod(
        instrument=SYMBOL, period_id="future", opened_at=later,
        closed_at=later+timedelta(days=1), available_at=later,
        source="future metadata", version="future-version"), source_index_at=later)
    extended = replace(original, bars=(*original.bars, bar(later)),
                       periods=(*original.periods, period))
    assert build(extended) == result
    assert build(replace(original, bars=original.bars[:-1])) == result


def test_missing_trading_period_is_not_compressed_into_yesterday():
    spec = daily()
    result = build(replace(spec, periods=(spec.periods[0], spec.periods[2])))
    assert result["blocker"] == "PERIOD_SEQUENCE_GAP"
    assert result["rows"] == []


def test_known_closed_day_can_be_omitted_without_inventing_prices():
    spec = daily()
    cal = replace(spec.session_schedule,
                  intervals=(spec.session_schedule.intervals[0], spec.session_schedule.intervals[2]))
    with_closed_period = build(replace(spec, session_schedule=cal))
    without_closed_period = build(replace(spec, session_schedule=cal,
                                        periods=(spec.periods[0], spec.periods[2])))
    assert with_closed_period["status"] == without_closed_period["status"] == "AVAILABLE"
    assert [r["source_index_at"] for r in with_closed_period["rows"]] == [
        "2020-01-01T00:00:00Z", "2020-01-03T00:00:00Z"]
    assert with_closed_period["rows"] == without_closed_period["rows"]


def test_delayed_base_bar_blocks_whole_daily_frame():
    spec = daily()
    delayed = replace(spec.bars[-2], available_at=T+2*STEP+US)
    result = build(replace(spec, bars=(*spec.bars[:-2], delayed, spec.bars[-1])))
    assert result["blocker"] == "HISTORY_GAP"
    assert result["rows"] == [] and result["observed_at"] is None


def test_current_period_must_exist_and_must_not_reuse_yesterday():
    spec = daily()
    absent = build(replace(spec, periods=spec.periods[:-1]))
    assert absent["blocker"] == "CURRENT_PERIOD_UNCOVERED"
    at_open = build(spec, T)
    assert at_open["status"] == "BLOCKED" and at_open["rows"] == []
    assert at_open["blocker"] == "NO_EXPECTED_BARS"
    at_end = build(spec, T+timedelta(days=1))
    assert at_end["blocker"] == "CURRENT_PERIOD_UNCOVERED"


def test_source_label_is_not_observation_or_publication_time():
    spec = daily()
    labels = tuple(replace(p, source_index_at=p.source_index_at+timedelta(hours=21))
                   for p in spec.periods)
    result = build(replace(spec, periods=labels))
    assert result["rows"][-1]["source_index_at"] == "2020-01-03T21:00:00Z"
    assert result["observed_at"] == result["available_at"] == "2020-01-03T00:10:00Z"


@pytest.mark.parametrize("hours", [23, 25])
def test_explicit_daily_elapsed_length_need_not_be_twenty_four_hours(hours):
    module = api()
    start = T-timedelta(hours=hours)
    prior = module.LabeledDailyPeriod(period=DailyPeriod(
        instrument=SYMBOL, period_id="prior", opened_at=start, closed_at=T,
        available_at=start, source="synthetic-DST", version="v1"), source_index_at=start)
    spec = daily()
    current = spec.periods[-1]
    data = (bar(start), bar(T))
    cal = schedule(start, T+timedelta(days=1), [(start,start+STEP),(T,T+STEP)])
    result = build(replace(spec, history_start=start, available_at=start,
                           bars=data, periods=(prior,current), session_schedule=cal), T+STEP)
    assert result["status"] == "AVAILABLE" and len(result["rows"]) == 2


def test_intraday_closed_and_forming_rows_are_rebuilt_from_base_prefix():
    spec = intraday()
    result = build(spec, T+7*STEP)
    assert result["status"] == "AVAILABLE"
    assert [r["state"] for r in result["rows"]] == ["CLOSED", "CLOSED", "FORMING"]
    assert [[r[k] for k in ("open","high","low","close","volume")]
            for r in result["rows"]] == [[100,104,99,103,3],[103,107,102,106,3],[106,108,105,107,1]]
    assert [r["observed_at"] for r in result["rows"]] == [
        "2020-01-03T00:15:00Z", "2020-01-03T00:30:00Z", "2020-01-03T00:35:00Z"]


@pytest.mark.parametrize("timeframe,count,last_state", [
    ("5m",7,"CLOSED"),("30m",2,"FORMING"),("1h",1,"FORMING"),("4h",1,"FORMING")])
def test_each_supported_map_grid_uses_same_known_base_prefix(timeframe,count,last_state):
    result = build(intraday(timeframe=timeframe), T+7*STEP)
    assert len(result["rows"]) == count
    assert result["rows"][-1]["state"] == last_state
    assert result["rows"][-1]["close"] == 107


def test_explicit_four_hour_origin_is_not_replaced_with_midnight():
    start = T-timedelta(hours=2)
    result = build(intraday(timeframe="4h", start=start), start+7*STEP)
    assert result["rows"][0]["source_index_at"] == "2020-01-02T22:00:00Z"
    assert result["rows"][0]["closed_at"] == "2020-01-03T02:00:00Z"


def test_future_intraday_payloads_do_not_change_earlier_frame():
    spec = intraday(12)
    early = build(spec, T+7*STEP)
    altered = replace(spec, bars=(*spec.bars[:7], *(
        replace(b, high=99999, close=88888) for b in spec.bars[7:])))
    assert build(altered, T+7*STEP) == early
    assert build(replace(spec, bars=spec.bars[:7]), T+7*STEP) == early


def test_scheduled_closure_is_not_a_missing_history_bar():
    spec = intraday(9)
    cal = replace(spec.session_schedule, intervals=(
        SessionInterval(opened_at=T, closed_at=T+3*STEP),
        SessionInterval(opened_at=T+6*STEP, closed_at=T+9*STEP)))
    result = build(replace(spec, session_schedule=cal), T+9*STEP)
    assert result["status"] == "AVAILABLE"
    assert [r["source_index_at"] for r in result["rows"]] == [
        "2020-01-03T00:00:00Z", "2020-01-03T00:30:00Z"]
    assert [r["volume"] for r in result["rows"]] == [3,3]


def test_missing_active_intraday_bar_blocks_instead_of_compressing_ema_history():
    spec = intraday()
    result = build(replace(spec, bars=(*spec.bars[:2],*spec.bars[3:])), T+7*STEP)
    assert result["blocker"] == "HISTORY_GAP" and result["rows"] == []


def test_unresolved_session_fragment_blocks_even_when_later_whole_bars_exist():
    spec = intraday()
    cal = replace(spec.session_schedule, intervals=(SessionInterval(
        opened_at=T+timedelta(minutes=1), closed_at=T+7*STEP),))
    result = build(replace(spec, session_schedule=cal), T+7*STEP)
    assert result["blocker"] == "FRAME_GRID_UNRESOLVED"


@pytest.mark.parametrize("budget,available", [(299,False),(300,True)])
def test_elapsed_freshness_is_explicit_in_a_known_closure(budget, available):
    result = build(replace(intraday(), max_age_seconds=budget), T+8*STEP)
    assert (result["status"] == "AVAILABLE") is available
    assert result["blocker"] == (None if available else "STALE")


def test_missing_volume_is_not_zero_and_overflow_is_not_publishable():
    spec = intraday()
    missing = build(replace(spec, bars=(replace(spec.bars[0],volume=None),*spec.bars[1:])), T+7*STEP)
    assert missing["rows"][0]["volume"] is None
    assert missing["rows"][1]["volume"] == 3
    with pytest.raises(ValueError, match="volume"):
        build(replace(spec, bars=tuple(replace(b,volume=1e308) for b in spec.bars)), T+7*STEP)


@pytest.mark.parametrize("kind", ["frame","calendar","period"])
def test_unavailable_metadata_blocks_prices(kind):
    spec = daily()
    if kind == "frame":
        spec = replace(spec,available_at=T+2*STEP+US)
    elif kind == "calendar":
        spec = replace(spec,session_schedule=replace(spec.session_schedule,available_at=T+2*STEP+US))
    else:
        spec = replace(spec,periods=(*spec.periods[:-1],replace(spec.periods[-1],
            period=replace(spec.periods[-1].period,available_at=T+2*STEP+US))))
    result = build(spec)
    assert result["status"] == "BLOCKED" and result["rows"] == []
    assert result["observed_at"] is result["available_at"] is None


@pytest.mark.parametrize("field,value", [
    ("frame_id",""),("source"," bad"),("version",None),("instrument","GC"),
    ("timeframe","2h"),("base_timeframe","1m"),("max_age_seconds",True),
    ("max_age_seconds",1.2),("max_age_seconds",-1),("bars",[]),
    ("periods",[]),("session_schedule",None),("grid_anchor",T),
    ("available_at",datetime(2020,1,1)),("history_start",pd.Timestamp("2020-01-01T00:00:00.000000001Z")),
])
def test_invalid_daily_contract_is_rejected(field,value):
    with pytest.raises(ValueError):
        replace(daily(),**{field:value})


@pytest.mark.parametrize("change", ["duplicate_bar","wrong_bar","duplicate_period","overlap","labels","wrong_period"])
def test_ambiguous_or_mixed_identity_history_is_rejected(change):
    spec = daily()
    with pytest.raises(ValueError):
        if change == "duplicate_bar":
            replace(spec,bars=(*spec.bars,spec.bars[-1]))
        elif change == "wrong_bar":
            replace(spec,bars=(*spec.bars[:-1],replace(spec.bars[-1],instrument="COMEX:GC")))
        elif change == "duplicate_period":
            replace(spec,periods=(*spec.periods,spec.periods[-1]))
        elif change == "overlap":
            replace(spec,periods=(*spec.periods[:-1],replace(spec.periods[-1],period=replace(
                spec.periods[-1].period,opened_at=T-STEP))))
        elif change == "labels":
            replace(spec,periods=(*spec.periods[:-1],replace(spec.periods[-1],source_index_at=spec.periods[0].source_index_at)))
        else:
            replace(spec,periods=(*spec.periods[:-1],replace(spec.periods[-1],period=replace(
                spec.periods[-1].period,instrument="COMEX:GC"))))


@pytest.mark.parametrize("change", ["origin_missing","origin_unaligned","history_unaligned","upsample","daily_periods"])
def test_invalid_intraday_grid_is_rejected(change):
    spec = intraday()
    with pytest.raises(ValueError):
        if change == "origin_missing":
            replace(spec,grid_anchor=None)
        elif change == "origin_unaligned":
            replace(spec,grid_anchor=T+US)
        elif change == "history_unaligned":
            replace(spec,history_start=T+STEP)
        elif change == "upsample":
            replace(spec,base_timeframe="30m")
        else:
            replace(spec,periods=daily().periods)


@pytest.mark.parametrize("decision", [T-3*timedelta(days=1),T+US,datetime(2020,1,3)])
def test_invalid_decision_time_is_rejected(decision):
    with pytest.raises(ValueError):
        build(daily(),decision)


def test_input_order_is_canonical_and_selected_revision_changes_hash():
    spec = daily()
    original = build(spec)
    assert build(replace(spec,bars=tuple(reversed(spec.bars)),periods=tuple(reversed(spec.periods)))) == original
    changed = replace(spec.bars[-2],high=116)
    revised = build(replace(spec,bars=(*spec.bars[:-2],changed,spec.bars[-1])))
    assert revised["evaluation_sha256"] != original["evaluation_sha256"]
    assert revised["rows"][-1]["high"] == 116


@pytest.mark.parametrize("value", [[], {}])
def test_unhashable_timeframe_is_a_contract_error(value):
    with pytest.raises(ValueError, match="timeframe"):
        replace(daily(),timeframe=value)


def test_empty_intraday_prefix_is_unavailable_and_zero_age_does_not_relax():
    spec = intraday()
    empty = build(spec,T)
    assert empty["blocker"] == "NO_EXPECTED_BARS" and empty["rows"] == []
    stale = build(spec,T+8*STEP)
    assert stale["blocker"] == "STALE" and stale["rows"] == []


def test_policy_and_grid_provenance_change_hash_without_revising_prices():
    spec = intraday()
    original = build(spec,T+7*STEP)
    for revised in (replace(spec,version="v2"),replace(spec,max_age_seconds=1)):
        result = build(revised,T+7*STEP)
        assert result["rows"] == original["rows"]
        assert result["evaluation_sha256"] != original["evaluation_sha256"]

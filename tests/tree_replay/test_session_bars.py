"""Synthetic interval schedules; no market data or calendar inference."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar

UTC = timezone.utc
T0 = datetime(2026, 9, 7, 20, 30, tzinfo=UTC)
STEP = timedelta(minutes=5)


def bar(t, close=128, tf="5m", **changes):
    duration = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}[tf]
    end = t + timedelta(minutes=duration)
    values = dict(instrument="SYNTH:TEST", timeframe=tf, opened_at=t,
                  closed_at=end, available_at=end, open=close, high=close+1,
                  low=close-0.5, close=close, volume=None, source="synthetic")
    return ClosedBar(**(values | changes))


def schedule(intervals=None, **changes):
    from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
    if intervals is None:
        intervals = ((T0, T0 + 6*STEP),
                     (T0 + 18*STEP, T0 + 30*STEP))
    values = dict(instrument="SYNTH:TEST", calendar_id="synthetic",
                  version="v1", source="synthetic declared hours",
                  coverage_start=T0, coverage_end=T0+30*STEP, available_at=T0,
                  intervals=tuple(SessionInterval(opened_at=a, closed_at=b)
                                  for a, b in intervals))
    return SessionSchedule(**(values | changes))


def select(bars, **changes):
    from trading_system.tree_replay.session_bars import select_session_bars
    values = dict(instrument="SYNTH:TEST", timeframe="5m", history_start=T0,
                  decision_time=T0+20*STEP, max_age_seconds=300,
                  session_schedule=schedule())
    return select_session_bars(bars, **(values | changes))


def complete_bars():
    return tuple(bar(T0+i*STEP) for i in (*range(6), 18, 19))


def test_scheduled_break_is_not_missing_history():
    r = select(complete_bars())
    assert r.blocker is None
    assert r.expected_bars == 8
    assert r.missing_opens == ()
    assert len(r.bars) == 8


@pytest.mark.parametrize("missing,blocker", [(0,"HISTORY_INCOMPLETE"),
                                            (3,"HISTORY_GAP"),(7,"HISTORY_GAP")])
def test_missing_leading_interior_and_latest_expected_bar_blocks(missing, blocker):
    bars = complete_bars()
    r = select(bars[:missing]+bars[missing+1:])
    assert r.blocker == blocker
    assert r.missing_opens == (bars[missing].opened_at,)


def test_delayed_expected_bar_is_missing_until_publication():
    bars = list(complete_bars())
    bars[-1] = replace(bars[-1], available_at=T0+20*STEP+timedelta(microseconds=1))
    r = select(bars)
    assert r.blocker == "HISTORY_GAP"
    assert r.missing_opens == (T0+19*STEP,)
    assert select(bars, decision_time=T0+20*STEP+timedelta(microseconds=1)).blocker is None


def test_no_observed_bars_in_open_schedule_is_incomplete_not_closed():
    r = select([])
    assert r.blocker == "HISTORY_INCOMPLETE"
    assert r.expected_bars == 8
    assert len(r.missing_opens) == 8


def test_all_closed_schedule_is_not_unknown_or_incomplete():
    r = select([], session_schedule=schedule(()))
    assert r.blocker == "NO_EXPECTED_BARS"
    assert r.expected_bars == 0


def test_out_of_session_rows_are_counted_and_never_used():
    r = select((*complete_bars(), bar(T0+10*STEP, close=999999)))
    assert r.blocker is None
    assert r.out_of_session_bars == 1
    assert all(b.close == 128 for b in r.bars)


def test_four_hour_bar_with_open_endpoints_but_internal_break_is_excluded():
    start = datetime(2026, 9, 7, 20, tzinfo=UTC)
    end = start+timedelta(hours=4)
    sc = schedule(((start,start+timedelta(hours=1)),(start+timedelta(hours=2),end)),
                  coverage_start=start, coverage_end=end)
    r = select([bar(start,tf="4h")], timeframe="4h", history_start=start,
               decision_time=end, session_schedule=sc)
    assert r.blocker == "NO_EXPECTED_BARS"
    assert r.straddling_bars == 1
    assert r.out_of_session_bars == 0
    assert r.bars == ()


@pytest.mark.parametrize("tf", ["5m","15m","30m","1h","4h"])
def test_full_interval_membership_and_close_boundary(tf):
    start = datetime(2026, 9, 7, 0, tzinfo=UTC)
    b = bar(start, tf=tf)
    sc = schedule(((start,b.closed_at),),coverage_start=start,coverage_end=b.closed_at,
                  available_at=start)
    r = select([b],timeframe=tf,history_start=start,decision_time=b.closed_at,
               session_schedule=sc)
    assert r.blocker is None
    assert r.expected_bars == 1


@pytest.mark.parametrize("field,value", [
    ("coverage_start", T0+STEP),("coverage_end",T0+19*STEP),
    ("available_at",T0+21*STEP)])
def test_uncovered_or_not_yet_known_calendar_blocks(field,value):
    # Empty intervals allow independently exercising each coverage boundary.
    sc = schedule((), **{field:value})
    r = select(complete_bars(), session_schedule=sc)
    assert r.blocker == ("CALENDAR_UNAVAILABLE" if field=="available_at" else "CALENDAR_COVERAGE")
    assert r.expected_bars == 0


def test_explicit_freshness_is_wall_clock_even_during_closure():
    bars = complete_bars()[:6]
    at = T0+7*STEP
    assert select(bars,decision_time=at).blocker is None
    assert select(bars,decision_time=at+timedelta(microseconds=1)).blocker == "STALE"
    assert select(bars,decision_time=at,max_age_seconds=10**30).blocker is None


@pytest.mark.parametrize("kind",["anchor","bar","identity","duplicate","schedule","nanosecond"])
def test_invalid_metadata_is_not_silently_reinterpreted(kind):
    bars = complete_bars()
    changes = {}
    if kind == "anchor": changes["history_start"] = T0+timedelta(seconds=1)
    if kind == "bar": bars = (*bars,bar(T0+timedelta(seconds=1)))
    if kind == "identity": changes["session_schedule"] = schedule(instrument="SYNTH:OTHER")
    if kind == "duplicate": bars = (*bars,bars[0])
    if kind == "schedule": changes["session_schedule"] = {}
    if kind == "nanosecond": changes["decision_time"] = pd.Timestamp(T0+20*STEP)+pd.Timedelta(1,"ns")
    with pytest.raises(ValueError):
        select(bars,**changes)


def test_future_rows_and_input_order_cannot_change_current_window():
    original = complete_bars()
    later = bar(T0+25*STEP,close=123456)
    assert select((*reversed(original),later)) == select(original)
    assert tuple(b.opened_at for b in original) == tuple(sorted(b.opened_at for b in original))


def test_schedule_fingerprint_changes_with_provenance_not_interval_input_order():
    a = schedule()
    b = replace(a,intervals=tuple(reversed(a.intervals)))
    assert select(complete_bars(),session_schedule=a) == select(complete_bars(),session_schedule=b)
    assert select(complete_bars(),session_schedule=replace(a,source="changed evidence")).schedule_sha256 != select(complete_bars()).schedule_sha256


def test_old_gap_outside_last_1600_bars_still_blocks_recursive_seed():
    end = T0+1700*STEP
    sc = schedule(((T0,end),),coverage_end=end)
    bars = tuple(bar(T0+i*STEP) for i in range(1700) if i != 2)
    r = select(bars,session_schedule=sc,decision_time=end)
    assert r.blocker == "HISTORY_GAP"
    assert r.missing_opens == (T0+2*STEP,)
    assert r.expected_bars == 1700

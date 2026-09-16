"""EMA integration against synthetic schedules; no actual-market performance claims."""
from dataclasses import replace
from datetime import timedelta, datetime, timezone
from pathlib import Path

import pytest

from test_session_bars import T0, STEP, bar, schedule
from trading_system.tree_replay.ema import ema_snapshot


def ten_bars():
    # Six bars, declared closure, then four bars: closes1..10 give EMA5=8.
    return tuple(bar(T0+i*STEP, close=c)
                 for i,c in zip((*range(6),18,19,20,21),range(1,11)))


def test_calendar_mode_requires_a_valid_schedule_contract():
    with pytest.raises(ValueError):
        snapshot(ten_bars(), session_schedule={})


def snapshot(bars, **changes):
    params = dict(snapshot_id="synthetic-session", instrument="SYNTH:TEST", timeframe="5m",
                  history_start=T0, decision_time=T0+22*STEP, max_age_seconds=300)
    return ema_snapshot(bars, **(params | changes))


def test_explicit_calendar_enables_same_formula_across_closure_without_changing_strict_default():
    bars = ten_bars()
    strict = snapshot(bars)
    assert strict["window_blocker"] == "HISTORY_GAP"
    r = snapshot(bars,session_schedule=schedule())
    assert r["window_blocker"] is None
    assert r["features"]["chartdesk.5m.ema5"] == pytest.approx(8)
    assert r["features"]["chartdesk.5m.ema5_delta5"] == pytest.approx(5)
    assert r["calendar"]["expected_bars"] == 10
    assert r["calendar"]["missing_opens"] == []
    assert r["coverage"]["selected_bars"] == 10
    assert "calendar" not in strict
    assert r["ready_for_replay"] is False
    assert r["ready_for_training"] is False


def test_calendar_and_all_bar_dependencies_control_feature_availability():
    bars = list(ten_bars())
    later = T0+22*STEP+timedelta(seconds=2)
    bars[0] = replace(bars[0],available_at=later-timedelta(seconds=1))
    sc = schedule(available_at=later)
    r = snapshot(bars,session_schedule=sc,decision_time=later)
    provenance = r["provenance"]["chartdesk.5m.ema5"]
    assert provenance["observed_at"] == "2026-09-07T22:20:00Z"
    assert provenance["available_at"] == "2026-09-07T22:20:02Z"
    r2 = snapshot(bars,session_schedule=schedule(),decision_time=later)
    assert r2["provenance"]["chartdesk.5m.ema5"]["available_at"] == "2026-09-07T22:20:01Z"


@pytest.mark.parametrize("reason",["missing","unpublished","coverage","closed","stale"])
def test_calendar_blockers_never_export_numerical_features(reason):
    bars = ten_bars()
    sc = schedule()
    changes = {}
    if reason=="missing": bars=bars[:2]+bars[3:]
    if reason=="unpublished": sc=replace(sc,available_at=T0+23*STEP)
    if reason=="coverage": sc=schedule((),coverage_end=T0+21*STEP)
    if reason=="closed": sc=schedule(())
    if reason=="stale":
        sc=schedule(((T0,T0+6*STEP),(T0+18*STEP,T0+22*STEP)))
        changes["decision_time"]=T0+23*STEP+timedelta(microseconds=1)
    r=snapshot(bars,session_schedule=sc,**changes)
    assert all(v is None for v in r["features"].values())
    assert set(r["availability"].values()) == ({"STALE"} if reason=="stale" else {"UNAVAILABLE"})
    assert r["ready_for_training"] is False


def test_future_suffix_and_snapshot_mutation_do_not_change_current_values():
    bars=ten_bars()
    sc=schedule()
    original=snapshot(bars,session_schedule=sc)
    again=snapshot((*bars,bar(T0+26*STEP,close=999999)),session_schedule=sc)
    assert original==again
    again["features"]["chartdesk.5m.ema5"]=42
    assert snapshot(bars,session_schedule=sc)==original


def test_calendar_evidence_is_in_hash_not_model_feature_columns():
    bars=ten_bars()
    a=snapshot(bars,session_schedule=schedule())
    b=snapshot(bars,session_schedule=schedule(source="different evidence"))
    assert a["features"]==b["features"]
    assert a["window_sha256"] != b["window_sha256"]
    assert a["calendar"]["schedule_sha256"] != b["calendar"]["schedule_sha256"]


def test_registered_normal_hours_bridge_connects_to_ema_without_market_inputs():
    from trading_system.data_foundation.sessions import load_session_calendar
    from trading_system.tree_replay.calendar import schedule_from_research_calendar
    root=Path(__file__).resolve().parents[2]
    template=load_session_calendar(root/"configs/data/session-calendar.yaml",
                                   "cme-globex-metals-research-v1")
    sc=schedule_from_research_calendar(
        template,instrument="SYNTH:TEST",coverage_start=T0,coverage_end=T0+30*STEP,
        available_at=T0,source="synthetic test binding; not market approval")
    r=snapshot(ten_bars(),session_schedule=sc)
    assert r["features"]["chartdesk.5m.ema5"]==pytest.approx(8)
    assert r["calendar"]["calendar_id"]=="cme-globex-metals-research-v1"


def test_weekend_does_not_reset_or_fill_ema():
    from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
    friday=datetime(2026,9,11,20,30,tzinfo=timezone.utc)
    sunday=datetime(2026,9,13,22,tzinfo=timezone.utc)
    end=sunday+4*STEP
    sc=SessionSchedule(instrument="SYNTH:TEST",calendar_id="synthetic",version="v1",
        coverage_start=friday,coverage_end=end,available_at=friday,source="synthetic weekend",
        intervals=(SessionInterval(opened_at=friday,closed_at=friday+6*STEP),
                   SessionInterval(opened_at=sunday,closed_at=end)))
    times=[friday+i*STEP for i in range(6)]+[sunday+i*STEP for i in range(4)]
    r=snapshot(tuple(bar(t,close=c) for t,c in zip(times,range(1,11))),
               history_start=friday,decision_time=end,session_schedule=sc)
    assert r["features"]["chartdesk.5m.ema5"]==pytest.approx(8)
    assert r["calendar"]["expected_bars"]==10

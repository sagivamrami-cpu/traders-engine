"""Actual decision clock is independent from closed-base price observation."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import inspect
import json

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.corrections import CorrectionEvidence
from trading_system.tree_replay.frames import FrameSpec, LabeledDailyPeriod, build_frame_asof
from trading_system.tree_replay.levelmap import MapFrameRequest, build_levelmap_asof
from trading_system.tree_replay.periods import DailyPeriod, aggregate_daily_asof


S = datetime(2026, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)
CLOSE = S+2*STEP
PUB = CLOSE+timedelta(seconds=20)
T = CLOSE+timedelta(seconds=30)
US = timedelta(microseconds=1)
SYMBOL = "OANDA:XAUUSD"


def fixture(timeframe="1d", hours=24):
    p = DailyPeriod(instrument=SYMBOL, period_id="day", opened_at=S,
                    closed_at=S+timedelta(hours=hours), available_at=S,
                    source="synthetic-period", version="v1")
    cal = SessionSchedule(instrument=SYMBOL, calendar_id="hours", version="v1",
        source="synthetic-calendar", coverage_start=S, coverage_end=S+timedelta(days=3),
        available_at=S, intervals=(SessionInterval(opened_at=S,closed_at=p.closed_at),))
    values = [(100,103,99,102),(102,107,101,106),(106,1000,1,900)]
    bars = tuple(ClosedBar(instrument=SYMBOL,timeframe="5m",opened_at=S+i*STEP,
        closed_at=S+(i+1)*STEP,available_at=PUB if i==1 else S+(i+1)*STEP,
        open=o,high=h,low=l,close=c,volume=10,source="synthetic")
        for i,(o,h,l,c) in enumerate(values))
    frame = FrameSpec(frame_id="daily" if timeframe=="1d" else timeframe,
        instrument=SYMBOL,timeframe=timeframe,base_timeframe="5m",history_start=S,
        available_at=S,source="synthetic-frame",version="v1",bars=bars,
        session_schedule=cal,max_age_seconds=370,
        periods=(LabeledDailyPeriod(period=p,source_index_at=S),) if timeframe=="1d" else (),
        grid_anchor=None if timeframe=="1d" else S)
    return frame


def call(kind, frame=None, decision=T, **kwargs):
    frame = fixture() if frame is None else frame
    fn = {"period":aggregate_daily_asof,"frame":build_frame_asof,"map":build_levelmap_asof}[kind]
    # Intended RED is missing capability, not an unrecognized-keyword exception.
    assert "closed_base_prefix" in inspect.signature(fn).parameters, "closed-prefix clock mode missing"
    if kind=="period":
        return fn(frame.bars,period=frame.periods[0].period,decision_time=decision,
                  base_timeframe=frame.base_timeframe,session_schedule=frame.session_schedule,**kwargs)
    if kind=="frame":
        return fn(frame,decision_time=decision,**kwargs)
    corr = CorrectionEvidence(evidence_id="correction",frame_id=frame.frame_id,instrument=SYMBOL,
        version="v1",observed_at=S,available_at=S,provenance="synthetic",offset=0,
        source="tv_daily",confidence="high",note="fixture")
    req = MapFrameRequest(timeframe="1d",lookback_days=400,frame=frame,correction=corr,
                          max_correction_age_seconds=200000)
    return fn(instrument=SYMBOL,decision_time=decision,requests=(req,),**kwargs)


@pytest.mark.parametrize("kind", ["period","frame","map"])
def test_delayed_closed_bar_is_known_at_real_clock_not_floor(kind):
    result = call(kind,closed_base_prefix=True)
    assert result["blocker"] is None
    if kind=="period":
        assert result["ohlcv"] == dict(open=100,high=107,low=99,close=106,volume=20)
        assert result["schema_version"] == "daily-period-prefix-asof-v1"
        assert result["calculation_version"] == "closed-lower-bars-daily-period-prefix-v1"
    elif kind=="frame":
        row = result["rows"][-1]
        assert [row[k] for k in ("open","high","low","close","volume")] == [100,107,99,106,20]
        assert row["state"] == "FORMING"
        assert result["schema_version"] == "historical-frame-prefix-asof-v1"
        assert result["calculation_version"] == "closed-base-frame-prefix-v1"
    else:
        assert result["status"] == "BUILT_UNADMITTED"
        assert result["schema_version"] == result["calculation_version"] == "historical-levelmap-prefix-asof-v1"
        assert result["level_snapshot"]["version"] == result["schema_version"]
        assert result["level_snapshot"]["observed_at"] == result["level_snapshot"]["available_at"] == "2026-01-01T00:10:30Z"
        assert {x["name"]:x["price"] for x in result["levels"]}["DAY-OPEN"] == 100
        result = result["fetch_trace"][0]["frame"]
    assert result["observed_at"] == "2026-01-01T00:10:00Z"
    assert result["available_at"] == "2026-01-01T00:10:20Z"
    assert result["observation_cutoff"] == "2026-01-01T00:10:00Z"


@pytest.mark.parametrize("kind", ["period","frame","map"])
def test_publication_boundary_does_not_receive_future_price_payload(kind):
    before = call(kind,decision=PUB-US,closed_base_prefix=True)
    assert before["status"] == "BLOCKED"
    if kind=="map":
        assert before["fetch_trace"][0]["blocker"] == "HISTORY_GAP"
        assert before["levels"] == [] and before["level_snapshot"] is None
    else:
        assert before["blocker"] == "HISTORY_GAP"
        assert before["observed_at"] is before["available_at"] is None
    frame = fixture()
    changed = replace(frame,bars=(frame.bars[0],replace(frame.bars[1],high=9999),frame.bars[2]))
    assert call(kind,frame=changed,decision=PUB-US,closed_base_prefix=True) == before
    assert call(kind,decision=PUB,closed_base_prefix=True)["blocker"] is None


@pytest.mark.parametrize("kind", ["period","frame","map"])
def test_future_suffix_does_not_change_prefix_result(kind):
    frame = fixture()
    original = call(kind,frame=frame,closed_base_prefix=True)
    changed = replace(frame,bars=frame.bars[:2]+(replace(frame.bars[2],high=99999,volume=99999),))
    assert call(kind,frame=changed,closed_base_prefix=True) == original
    assert call(kind,frame=replace(frame,bars=frame.bars[:2]),closed_base_prefix=True) == original
    json.dumps(original,allow_nan=False)
    assert not original["ready_for_training"] and not original["ready_for_replay"]


@pytest.mark.parametrize("kind", ["period","frame","map"])
def test_strict_default_compatibility_and_explicit_mode_version(kind):
    frame = fixture()
    frame = replace(frame,bars=tuple(replace(b,available_at=b.closed_at) for b in frame.bars))
    plain = call(kind,frame=frame,decision=CLOSE)
    assert call(kind,frame=frame,decision=CLOSE,closed_base_prefix=False) == plain
    assert "observation_cutoff" not in plain
    prefix = call(kind,frame=frame,decision=CLOSE,closed_base_prefix=True)
    assert prefix["evaluation_sha256"] != plain["evaluation_sha256"]
    if kind=="map":
        assert prefix["levels"] == plain["levels"]
        assert call(kind,closed_base_prefix=False)["blocker"] == "FRAME_CALCULATION_ERROR"
    else:
        with pytest.raises(ValueError,match="grid"):
            call(kind,closed_base_prefix=False)


def test_prechange_default_hashes_are_preserved():
    import test_periods as p
    import test_frames as f
    import test_levelmap as m
    assert p.run(*p.fixture())["evaluation_sha256"] == "48ffeb5bce9baa912b2d5080ba9bd9b65a11d67758d646a31c0c0ea7a811829a"
    assert f.build(f.daily())["evaluation_sha256"] == "fa221a0265d0ef2c5acc1bcb5cbf300cd98a2467a84ebb196780ff9fe471f0be"
    assert m.build((m.request(m.daily(16),400),))["evaluation_sha256"] == "a64b1f01d24b8ffd88ad63daef2b3b374a6ec1436781bbf25db045b49906ba6f"


@pytest.mark.parametrize("kind", ["period","frame","map"])
@pytest.mark.parametrize("value", [0,1,None,"true",[],{}])
def test_prefix_policy_requires_actual_boolean(kind,value):
    with pytest.raises(ValueError,match="closed_base_prefix"):
        call(kind,closed_base_prefix=value)


@pytest.mark.parametrize("kind", ["period","frame","map"])
@pytest.mark.parametrize("decision", [T.replace(tzinfo=None),pd.Timestamp(T)+pd.Timedelta(nanoseconds=1)])
def test_new_clock_retains_timezone_and_microsecond_precision(kind,decision):
    with pytest.raises(ValueError):
        call(kind,decision=decision,closed_base_prefix=True)


@pytest.mark.parametrize("tf", ["15m","1h","4h"])
def test_forming_intraday_rows_do_not_consume_partial_base_final_prices(tf):
    out = call("frame",frame=fixture(tf),closed_base_prefix=True)
    assert out["status"] == "AVAILABLE" and len(out["rows"])==1
    row = out["rows"][0]
    assert [row[k] for k in ("open","high","low","close","volume")] == [100,107,99,106,20]
    assert row["state"] == "FORMING" and row["source_index_at"] == "2026-01-01T00:00:00Z"
    assert row["observed_at"] == "2026-01-01T00:10:00Z"


@pytest.mark.parametrize("kind", ["frame","map"])
def test_freshness_uses_actual_clock_and_exact_budget(kind):
    frame = fixture()
    cal = replace(frame.session_schedule,intervals=(SessionInterval(opened_at=S,closed_at=CLOSE),))
    frame = replace(frame,session_schedule=cal)
    at = CLOSE+timedelta(seconds=370)
    assert call(kind,frame=frame,decision=at,closed_base_prefix=True)["blocker"] is None
    stale = call(kind,frame=frame,decision=at+US,closed_base_prefix=True)
    assert stale["blocker"] == ("STALE" if kind=="frame" else "REQUIRED_DAILY_INPUT_UNAVAILABLE")
    zero = replace(frame,max_age_seconds=0)
    assert call(kind,frame=zero,decision=T,closed_base_prefix=True)["status"] == "BLOCKED"


@pytest.mark.parametrize("kind,what", [
    ("period","calendar"),("period","period"),
    ("frame","calendar"),("frame","period"),("frame","frame"),
    ("map","calendar"),("map","period"),("map","frame"),
])
def test_metadata_published_between_close_and_decision_is_not_backdated(kind,what):
    frame = fixture()
    if what=="calendar":
        frame = replace(frame,session_schedule=replace(frame.session_schedule,available_at=PUB))
    elif what=="period":
        frame = replace(frame,periods=(replace(frame.periods[0],period=replace(frame.periods[0].period,available_at=PUB)),))
    else:
        frame = replace(frame,available_at=PUB)
    assert call(kind,frame=frame,decision=PUB-US,closed_base_prefix=True)["status"] == "BLOCKED"
    out = call(kind,frame=frame,closed_base_prefix=True)
    assert out["blocker"] is None
    trace = out["fetch_trace"][0]["frame"] if kind=="map" else out
    assert trace["available_at"] == "2026-01-01T00:10:20Z"


@pytest.mark.parametrize("tf", ["1d","15m"])
def test_calendar_coverage_cannot_end_at_price_floor_before_actual_T(tf):
    frame = fixture(tf)
    cal = replace(frame.session_schedule,coverage_end=CLOSE,
                  intervals=(SessionInterval(opened_at=S,closed_at=CLOSE),))
    out = call("frame",frame=replace(frame,session_schedule=cal),closed_base_prefix=True)
    assert out["blocker"] == "CALENDAR_COVERAGE" and out["rows"] == []


@pytest.mark.parametrize("hours", [23,25])
def test_prefix_respects_supplied_period_lengths(hours):
    frame = fixture(hours=hours)
    out = call("frame",frame=frame,closed_base_prefix=True)
    assert out["rows"][0]["closed_at"] == (S+timedelta(hours=hours)).isoformat().replace("+00:00","Z")
    assert out["rows"][0]["close"] == 106


def test_current_period_is_not_replaced_by_previous_day_at_rollover():
    frame = fixture()
    assert call("frame",frame=frame,decision=S+timedelta(seconds=30),closed_base_prefix=True)["blocker"] == "NO_EXPECTED_BARS"
    assert call("frame",frame=frame,decision=S+timedelta(days=1,seconds=30),closed_base_prefix=True)["blocker"] == "CURRENT_PERIOD_UNCOVERED"


def test_source_session_uses_actual_clock_with_unchanged_price_prefix():
    import test_levelmap as m
    requests=[]
    for req in m.inputs(16):
        cal = req.frame.session_schedule
        intervals=tuple(SessionInterval(opened_at=i.opened_at,closed_at=min(i.closed_at,m.T))
                        for i in cal.intervals if i.opened_at<m.T)
        requests.append(replace(req,frame=replace(req.frame,session_schedule=replace(cal,intervals=intervals))))
    before = m.T+timedelta(hours=1,minutes=30)-US
    assert "closed_base_prefix" in inspect.signature(build_levelmap_asof).parameters
    a = build_levelmap_asof(instrument=SYMBOL,decision_time=before,requests=tuple(requests),closed_base_prefix=True)
    b = build_levelmap_asof(instrument=SYMBOL,decision_time=before+US,requests=tuple(requests),closed_base_prefix=True)
    assert a["status"] == b["status"] == "BUILT_UNADMITTED"
    assert "LONDON-OPEN" in {x["name"] for x in a["levels"]}
    assert "LONDON-OPEN" not in {x["name"] for x in b["levels"]}
    assert "NY-OPEN" in {x["name"] for x in b["levels"]}
    assert a["fetch_trace"][1]["frame"]["observed_at"] == b["fetch_trace"][1]["frame"]["observed_at"] == "2026-09-09T14:00:00Z"
    assert b["level_snapshot"]["observed_at"] == "2026-09-09T15:30:00Z"


def test_future_daily_period_extension_does_not_change_prefix_hash():
    frame = fixture()
    p = frame.periods[0].period
    future = LabeledDailyPeriod(source_index_at=p.closed_at,period=replace(
        p,period_id="tomorrow",opened_at=p.closed_at,closed_at=p.closed_at+timedelta(days=1)))
    extended = replace(frame,periods=frame.periods+(future,))
    assert call("frame",frame=extended,closed_base_prefix=True) == call("frame",frame=frame,closed_base_prefix=True)


@pytest.mark.parametrize("tf", ["1d","15m"])
def test_missing_expected_prefix_history_is_not_compressed(tf):
    frame = fixture(tf)
    incomplete = replace(frame,bars=frame.bars[1:])
    result = call("frame",frame=incomplete,closed_base_prefix=True)
    assert result["blocker"] == "HISTORY_INCOMPLETE" and result["rows"] == []
    # The same absent interval is not a hole when independently supplied as closed.
    cal = replace(frame.session_schedule,intervals=(SessionInterval(opened_at=S+STEP,closed_at=S+3*STEP),))
    result = call("frame",frame=replace(incomplete,session_schedule=cal),closed_base_prefix=True)
    assert result["status"] == "AVAILABLE"
    assert result["rows"][0]["open"] == 102 and result["rows"][0]["close"] == 106


def test_current_empty_period_cannot_inherit_previous_daily_prices():
    frame = fixture()
    p = frame.periods[0].period
    following = LabeledDailyPeriod(source_index_at=p.closed_at,period=replace(
        p,period_id="next",opened_at=p.closed_at,closed_at=p.closed_at+timedelta(days=1)))
    cal = replace(frame.session_schedule,intervals=(
        SessionInterval(opened_at=S,closed_at=S+3*STEP),
        SessionInterval(opened_at=p.closed_at,closed_at=p.closed_at+STEP)))
    frame = replace(frame,periods=frame.periods+(following,),session_schedule=cal,max_age_seconds=100000)
    out = call("frame",frame=frame,decision=p.closed_at+timedelta(seconds=30),closed_base_prefix=True)
    assert out["blocker"] == "NO_EXPECTED_BARS" and out["rows"] == []


@pytest.mark.parametrize("hours", [23,25])
def test_completed_non24h_period_keeps_actual_late_publication(hours):
    frame = fixture(hours=hours)
    p = frame.periods[0].period
    cal = replace(frame.session_schedule,intervals=(SessionInterval(opened_at=S,closed_at=S+3*STEP),))
    publication = p.closed_at+timedelta(seconds=20)
    frame = replace(frame,session_schedule=cal,bars=frame.bars[:2]+(
        replace(frame.bars[2],available_at=publication),))
    before = call("period",frame=frame,decision=publication-US,closed_base_prefix=True)
    assert before["blocker"] == "HISTORY_GAP" and before["ohlcv"] is None
    after = call("period",frame=frame,decision=publication,closed_base_prefix=True)
    assert after["status"] == "CLOSED" and after["ohlcv"]["high"] == 1000
    assert after["observation_cutoff"] == p.closed_at.isoformat().replace("+00:00","Z")
    assert after["available_at"] == publication.isoformat().replace("+00:00","Z")

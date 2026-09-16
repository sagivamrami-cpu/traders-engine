"""Synthetic, offline as-of reversal contract tests; no market performance claims."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.levels import NamedLevel, LevelSnapshot
from trading_system.tree_replay.reversal import detect_reversals_asof


UTC = timezone.utc
START = datetime(2026, 9, 7, 10, 30, tzinfo=UTC)
INSTRUMENT = "CME:GC"


def history(timeframe="5m", short=False):
    minutes = 5 if timeframe == "5m" else 15
    rows = ([[103, 104, 102, 103, 100]] * 11 +
            [[103, 103.5, 96, 98, 350], [98, 102, 97.5, 101, 120]])
    if timeframe == "15m":
        rows = [[103, 108, 98, 103, 100]] * 11 + [[103, 103, 99, 101, 160]]
    bars = []
    for i, (o, h, l, c, v) in enumerate(rows):
        if short:
            o, h, l, c = 200-o, 200-l, 200-h, 200-c
        opened = START + timedelta(minutes=minutes*i)
        closed = opened + timedelta(minutes=minutes)
        bars.append(ClosedBar(instrument=INSTRUMENT, timeframe=timeframe,
                              opened_at=opened, closed_at=closed, available_at=closed,
                              open=o, high=h, low=l, close=c, volume=v, source="synthetic"))
    return bars


def levels(bars, **changes):
    args = dict(snapshot_id="levels-1", instrument=INSTRUMENT, version="fixture-v1",
                observed_at=bars[-1].closed_at, available_at=bars[-1].closed_at,
                source="synthetic-levels", levels=(NamedLevel(name="PSY-LO", price=100),))
    args.update(changes)
    return LevelSnapshot(**args)


def run(bars=None, **changes):
    bars = history() if bars is None else bars
    args = dict(snapshot_id="evaluation-1", instrument=INSTRUMENT,
                timeframe=bars[0].timeframe, decision_time=bars[-1].closed_at,
                history_start=bars[0].opened_at, max_age_seconds=370,
                level_snapshot=levels(bars), max_level_age_seconds=370)
    args.update(changes)
    return detect_reversals_asof(bars, **args)


@pytest.mark.parametrize("tf,short,kind,pattern", [
    ("5m", False, "red", "two_bar_reclaim"),
    ("5m", True, "green", "two_bar_reject"),
    ("15m", False, "violet", "single_bar_reclaim"),
    ("15m", True, "blue", "single_bar_reject"),
])
def test_original_source_setups_are_unpriced(tf, short, kind, pattern):
    bars = history(tf, short)
    result = run(bars)
    assert result["status"] == "DETECTED_UNPRICED"
    assert result["blocker"] is None
    assert len(result["candidates"]) == 1
    c = result["candidates"][0]
    assert c["direction"] == ("SHORT" if short else "LONG")
    assert c["source_direction"] == ("שורט" if short else "לונג")
    assert c["pattern"] == pattern and c["vector_kind"] == kind
    assert c["level_price"] == 100 and c["tradeable"] is False
    assert c["trade_plan"] is None
    assert not result["ready_for_training"] and not result["ready_for_replay"]
    assert "label" not in c and "success" not in c and "entry_fill" not in c
    features = c["snapshot"]["features"]
    assert features["reversal.vector_volume_ratio"] == pytest.approx(1.6 if tf == "15m" else 3.5)
    assert features["reversal.vector_volume"] == (160 if tf == "15m" else 350)
    assert features["reversal.vector_prior_avg_volume_10"] == 100
    assert all(p["phase"] == "PRE_ENTRY" for p in c["snapshot"]["provenance"].values())
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("name", ["EMA50-5m", "EMA200-1h-extra", "QUARTER", "OTHER"])
def test_ineligible_levels_are_not_failed_trades(name):
    bars = history()
    result = run(bars, level_snapshot=levels(bars, levels=(NamedLevel(name=name, price=100),)))
    assert result["status"] == "NO_CANDIDATE" and result["candidates"] == []


@pytest.mark.parametrize("name", ["CLOUD50-1h", "CLOUD50-4h", "EMA200-1h", "EMA800-4h", "YDAY-LO"])
def test_source_eligible_levels(name):
    bars = history()
    assert run(bars, level_snapshot=levels(bars, levels=(NamedLevel(name=name, price=100),)))["status"] == "DETECTED_UNPRICED"


def test_empty_levels_are_known_negative_but_missing_levels_block():
    bars = history()
    assert run(bars, level_snapshot=levels(bars, levels=()))["status"] == "NO_CANDIDATE"
    result = run(bars, level_snapshot=None)
    assert result["status"] == "BLOCKED" and result["blocker"] == "LEVELS_UNAVAILABLE"


@pytest.mark.parametrize("change,blocker", [
    ({"level_snapshot": None}, "LEVELS_UNAVAILABLE"),
    ({"max_age_seconds": 1, "decision_offset": 2}, "STALE"),
    ({"max_level_age_seconds": 1, "decision_offset": 2}, "LEVELS_STALE"),
])
def test_blocked_has_no_candidate_features(change, blocker):
    bars = history()
    change = dict(change)
    decision = bars[-1].closed_at + timedelta(seconds=change.pop("decision_offset", 0))
    result = run(bars, decision_time=decision, **change)
    assert result["blocker"] == blocker and result["status"] == "BLOCKED"
    assert result["candidates"] == []


def test_future_levels_block_and_levels_after_confirmation_are_not_backfilled():
    bars = history()
    close = bars[-1].closed_at
    late = levels(bars, available_at=close + timedelta(seconds=1))
    assert run(bars, level_snapshot=late)["blocker"] == "LEVELS_UNAVAILABLE"
    revised = levels(bars, observed_at=close+timedelta(seconds=1), available_at=close+timedelta(seconds=1))
    assert run(bars, decision_time=close+timedelta(seconds=2), level_snapshot=revised)["blocker"] == "LEVELS_AFTER_CONFIRMATION"


def test_late_published_inputs_record_actual_availability_not_confirmation():
    bars = history()
    close = bars[-1].closed_at
    bars[0] = replace(bars[0], available_at=close+timedelta(seconds=1))
    late = levels(bars, available_at=close+timedelta(seconds=2))
    result = run(bars, decision_time=close+timedelta(seconds=3), level_snapshot=late)
    c = result["candidates"][0]
    assert c["confirmed_at"] == close.isoformat().replace("+00:00", "Z")
    expected = (close+timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    assert all(p["available_at"] == expected for p in c["snapshot"]["provenance"].values())


def test_future_bars_do_not_change_evaluation_and_unfinished_confirmation_does_not_trigger():
    bars = history()
    close = bars[-1].closed_at
    future = replace(bars[-1], opened_at=close, closed_at=close+timedelta(minutes=5), available_at=close+timedelta(minutes=5))
    result = run(bars)
    assert run(bars+[future], decision_time=close, level_snapshot=levels(bars)) == result
    assert run(bars, decision_time=close-timedelta(microseconds=1), level_snapshot=levels(bars[:-1]))["candidates"] == []


def test_current_levels_cannot_resurrect_an_old_confirmation():
    bars = history()
    close = bars[-1].closed_at
    following = replace(bars[-1], opened_at=close, closed_at=close+timedelta(minutes=5),
                        available_at=close+timedelta(minutes=5), open=103, high=104, low=102, close=103, volume=100)
    result = run(bars+[following])
    assert result["status"] == "NO_CANDIDATE"


@pytest.mark.parametrize("index", [0, 5, -1])
def test_missing_volume_is_not_zero(index):
    bars = history()
    bars[index] = replace(bars[index], volume=None)
    assert run(bars)["blocker"] == "VOLUME_UNAVAILABLE"


def test_zero_volume_history_blocks():
    assert run([replace(b, volume=0) for b in history()])["blocker"] == "VOLUME_UNAVAILABLE"


def test_undefined_volume_ratio_is_explicit_unknown_not_infinity():
    bars = history()
    bars[:11] = [replace(b, volume=0) for b in bars[:11]]
    c = run(bars)["candidates"][0]
    assert c["snapshot"]["features"]["reversal.vector_volume_ratio"] is None
    assert c["snapshot"]["availability"]["reversal.vector_volume_ratio"] == "UNKNOWN"
    json.dumps(c, allow_nan=False)


@pytest.mark.parametrize("index", [0, 5, -1])
def test_late_history_bar_blocks(index):
    bars = history()
    close = bars[-1].closed_at
    bars[index] = replace(bars[index], available_at=close+timedelta(seconds=1))
    result = run(bars)
    # A late tail is unselected; its older predecessor may still be fresh.
    assert not result["candidates"]
    if index != -1:
        assert result["status"] == "BLOCKED"


def test_gap_and_warmup_are_distinct_from_a_negative_signal():
    bars = history()
    assert run(bars[:5]+bars[6:])["blocker"] == "HISTORY_GAP"
    assert run(bars[:11])["blocker"] == "WARMUP"


def test_nearest_level_and_equal_price_tie_preserve_source_input_order():
    bars = history()
    a = NamedLevel(name="PSY-LO", price=100)
    b = NamedLevel(name="YDAY-LO", price=100.5)
    assert run(bars, level_snapshot=levels(bars, levels=(a,b)))["candidates"][0]["level_name"] == b.name
    b = replace(b, price=100)
    for ordered in [(a,b), (b,a)]:
        assert run(bars, level_snapshot=levels(bars, levels=ordered))["candidates"][0]["level_name"] == ordered[0].name


def test_source_event_bucket_is_not_silently_changed_to_confirmation_bucket():
    c = run()["candidates"][0]
    assert c["source_event_id"] == "CME:GC|לונג|2026-09-07T11:15:00+00:00"
    assert c["confirmed_at"] == "2026-09-07T11:35:00Z"


def test_identity_is_stable_but_evaluation_tracks_inputs_policies_and_time():
    bars = history()
    first = run(bars)
    later = run(bars, decision_time=bars[-1].closed_at+timedelta(seconds=1))
    assert first["candidates"][0]["candidate_id"] == later["candidates"][0]["candidate_id"]
    assert first["evaluation_sha256"] != later["evaluation_sha256"]
    for changes in [dict(max_level_age_seconds=400), dict(max_age_seconds=400),
                    dict(level_snapshot=levels(bars, source="different-source"))]:
        assert run(bars, **changes)["evaluation_sha256"] != first["evaluation_sha256"]
    assert run(list(reversed(bars)), history_start=bars[0].opened_at,
               decision_time=bars[-1].closed_at, level_snapshot=levels(bars)) == first


@pytest.mark.parametrize("field", ["snapshot_id", "version", "source"])
@pytest.mark.parametrize("value", ["", " bad", "bad ", None, 1])
def test_level_metadata_invalid(field, value):
    with pytest.raises(ValueError):
        levels(history(), **{field:value})


@pytest.mark.parametrize("value", [True, None, "100", float("nan"), float("inf"), -1, 0])
def test_invalid_level_prices(value):
    with pytest.raises(ValueError):
        NamedLevel(name="PSY-LO", price=value)


@pytest.mark.parametrize("value", ["", " x", "x ", None, 1])
def test_invalid_level_names(value):
    with pytest.raises(ValueError):
        NamedLevel(name=value, price=100)


def test_level_contract_is_immutable_and_validates_time_identity_and_duplicates():
    bars = history()
    ls = levels(bars)
    with pytest.raises(FrozenInstanceError):
        ls.source = "changed"
    with pytest.raises(ValueError):
        levels(bars, levels=ls.levels*2)
    with pytest.raises(ValueError):
        levels(bars, levels=[ls.levels[0]])
    with pytest.raises(ValueError):
        levels(bars, levels=(object(),))
    with pytest.raises(ValueError):
        levels(bars, available_at=ls.observed_at-timedelta(seconds=1))
    with pytest.raises(ValueError):
        levels(bars, observed_at=ls.observed_at.replace(tzinfo=None))
    with pytest.raises(ValueError):
        levels(bars, observed_at=pd.Timestamp(ls.observed_at)+pd.Timedelta(nanoseconds=1))
    with pytest.raises(ValueError):
        levels(bars, instrument="GC")
    with pytest.raises(ValueError):
        run(bars, level_snapshot=levels(bars, instrument="CME:ES"))


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, None, "370"])
def test_explicit_level_freshness_budget(value):
    with pytest.raises(ValueError):
        run(max_level_age_seconds=value)


@pytest.mark.parametrize("value", ["", " bad", "bad ", None, 1])
def test_evaluation_id_validation(value):
    with pytest.raises(ValueError):
        run(snapshot_id=value)


def test_wrong_types_and_duplicates_fail_before_silent_source_normalization():
    bars = history()
    for changes in [dict(timeframe="30m"), dict(level_snapshot={}), dict(instrument="GC")]:
        with pytest.raises(ValueError):
            run(bars, **changes)
    with pytest.raises(ValueError):
        run(bars+[bars[0]])
    with pytest.raises(ValueError):
        run(bars+[replace(bars[0], instrument="CME:ES")])


def test_microsecond_freshness_and_exact_boundary():
    bars = history()
    close = bars[-1].closed_at
    assert run(bars, decision_time=close+timedelta(seconds=370))["status"] == "DETECTED_UNPRICED"
    assert run(bars, decision_time=close+timedelta(seconds=370, microseconds=1))["blocker"] == "STALE"
    assert run(bars, decision_time=close+timedelta(seconds=370, microseconds=1), max_age_seconds=400)["blocker"] == "LEVELS_STALE"


def test_numeric_overflow_fails_closed():
    bars = history()
    bars[0] = replace(bars[0], volume=1e308)
    with pytest.raises(ValueError, match="numeric"):
        run(bars)


def schedule(bars, **changes):
    args = dict(instrument=INSTRUMENT, calendar_id="synthetic", version="v1",
                coverage_start=bars[0].opened_at,
                coverage_end=bars[-1].closed_at+timedelta(minutes=5),
                available_at=bars[0].opened_at, source="synthetic-schedule",
                intervals=(SessionInterval(opened_at=bars[0].opened_at,
                                           closed_at=bars[-1].closed_at+timedelta(minutes=5)),))
    args.update(changes)
    return SessionSchedule(**args)


def session_gap(bars, at):
    shift = timedelta(minutes=30)
    moved = bars[:at]+[replace(b, opened_at=b.opened_at+shift,
                              closed_at=b.closed_at+shift, available_at=b.available_at+shift)
                      for b in bars[at:]]
    cal = schedule(moved, intervals=(
        SessionInterval(opened_at=moved[0].opened_at, closed_at=moved[at-1].closed_at),
        SessionInterval(opened_at=moved[at].opened_at, closed_at=moved[-1].closed_at),
    ))
    return moved, cal


@pytest.mark.parametrize("tf", ["5m", "15m"])
def test_supplied_closed_session_in_seed_preserves_source_pvsra(tf):
    bars, cal = session_gap(history(tf), 5)
    assert run(bars)["blocker"] == "HISTORY_GAP"
    result = run(bars, session_schedule=cal)
    assert result["status"] == "DETECTED_UNPRICED"
    assert result["calendar"]["expected_bars"] == len(bars)
    assert result["calendar"]["missing_opens"] == []
    assert not result["calendar"]["execution_truth"]


@pytest.mark.parametrize("tf,at", [("5m",11), ("5m",12), ("15m",11)])
def test_closed_session_does_not_turn_nonadjacent_bars_into_pattern(tf, at):
    bars, cal = session_gap(history(tf), at)
    result = run(bars, session_schedule=cal)
    assert result["status"] == "NO_CANDIDATE" and result["blocker"] is None


def test_calendar_missing_open_bar_blocks_and_late_calendar_is_not_used():
    bars = history()
    cal = schedule(bars)
    missing = run(bars[:5]+bars[6:], session_schedule=cal)
    assert missing["blocker"] == "HISTORY_GAP"
    assert len(missing["calendar"]["missing_opens"]) == 1
    late = replace(cal, available_at=bars[-1].closed_at+timedelta(seconds=1))
    assert run(bars, session_schedule=late)["blocker"] == "CALENDAR_UNAVAILABLE"


def test_calendar_publication_propagates_to_feature_dependencies_and_hash():
    bars = history()
    cal = schedule(bars)
    first = run(bars, session_schedule=cal)
    when = bars[-1].closed_at+timedelta(seconds=2)
    late = replace(cal, available_at=when)
    result = run(bars, session_schedule=late, decision_time=when)
    assert result["evaluation_sha256"] != first["evaluation_sha256"]
    expected = when.isoformat().replace("+00:00", "Z")
    assert all(p["available_at"] == expected for p in result["candidates"][0]["snapshot"]["provenance"].values())


@pytest.mark.parametrize("tf,short", [("5m",False), ("5m",True), ("15m",False), ("15m",True)])
def test_wrong_arrival_side_does_not_trigger(tf, short):
    bars = history(tf, short)
    prior_index = -3 if tf == "5m" else -2
    price = 101 if short else 99
    bars[prior_index] = replace(bars[prior_index], open=price, close=price, low=98, high=102)
    assert run(bars)["status"] == "NO_CANDIDATE"


@pytest.mark.parametrize("short", [False, True])
def test_m5_rising_volume_vector_is_not_accepted(short):
    bars = history(short=short)
    # Wider prior bars make prior spread-volume larger than vector SV, so the
    # 160% vector is rising (violet/blue), not a spread-volume climax.
    bars[:11] = [replace(b, high=110, low=90) for b in bars[:11]]
    bars[-2] = replace(bars[-2], volume=160)
    assert run(bars)["status"] == "NO_CANDIDATE"


@pytest.mark.parametrize("short", [False, True])
def test_m5_confirmation_must_close_back_through_level(short):
    bars = history(short=short)
    bars[-1] = replace(bars[-1], close=101 if short else 99)
    assert run(bars)["status"] == "NO_CANDIDATE"


def test_empty_history_has_no_history_blocker():
    bars = history()
    result = detect_reversals_asof([], snapshot_id="empty", instrument=INSTRUMENT,
                                   timeframe="5m", decision_time=bars[-1].closed_at,
                                   history_start=START, max_age_seconds=370,
                                   level_snapshot=levels(bars), max_level_age_seconds=370)
    assert result["blocker"] == "NO_HISTORY" and result["candidates"] == []

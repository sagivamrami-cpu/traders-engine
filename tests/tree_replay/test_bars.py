"""Synthetic boundary scenarios; no market data or source-repository imports."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo

import pytest
import pandas as pd


START = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


@pytest.fixture
def api():
    import trading_system.tree_replay.bars as bars

    return bars


def make_bar(api, minute=0, **changes):
    values = dict(
        instrument="SYNTH:TEST", timeframe="5m",
        opened_at=START + timedelta(minutes=minute),
        closed_at=START + timedelta(minutes=minute + 5),
        available_at=START + timedelta(minutes=minute + 5),
        open=100, high=103, low=99, close=102, volume=None,
        source="synthetic:fixture",
    )
    values.update(changes)
    return api.ClosedBar(**values)


def select(api, bars=(), **changes):
    request = dict(
        instrument="SYNTH:TEST", timeframe="5m", history_start=START,
        decision_time=START + timedelta(minutes=10), max_age_seconds=300,
    )
    request.update(changes)
    return api.select_closed_bars(bars, **request)


def test_closed_bar_retains_missing_volume_and_normalizes_native_prices(api):
    bar = make_bar(api)
    assert (bar.open, bar.high, bar.low, bar.close) == (100.0, 103.0, 99.0, 102.0)
    assert all(type(getattr(bar, name)) is float for name in ("open", "high", "low", "close"))
    assert bar.volume is None


@pytest.mark.parametrize("volume", [0, 0.0, 12, 12.5])
def test_finite_nonnegative_volume_is_preserved(api, volume):
    assert make_bar(api, volume=volume).volume == volume


@pytest.mark.parametrize("field", ["open", "high", "low", "close", "volume"])
@pytest.mark.parametrize("value", [True, False, "100", [], {}, Decimal("100"), Fraction(100), float("nan"), float("inf"), -float("inf"), 10**400])
def test_invalid_numeric_values_are_rejected(api, field, value):
    with pytest.raises(ValueError):
        make_bar(api, **{field: value})


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
@pytest.mark.parametrize("value", [None, 0, -1])
def test_prices_must_be_positive(api, field, value):
    with pytest.raises(ValueError):
        make_bar(api, **{field: value})


def test_negative_volume_is_rejected(api):
    with pytest.raises(ValueError):
        make_bar(api, volume=-0.1)


@pytest.mark.parametrize("changes", [{"open": 104}, {"open": 98}, {"close": 104}, {"close": 98}, {"low": 104}, {"high": 98}])
def test_ohlc_geometry_is_validated(api, changes):
    with pytest.raises(ValueError):
        make_bar(api, **changes)


def test_flat_bar_and_boundary_prices_are_valid(api):
    assert make_bar(api, open=100, high=100, low=100, close=100).close == 100.0
    assert make_bar(api, open=99, close=103).close == 103.0


@pytest.mark.parametrize("field,values", [
    ("instrument", [None, 123, "", "TEST", ":TEST", "SYNTH:", "SYNTH:TEST:X", " SYNTH:TEST", "SYNTH:TEST ", "SYN TH:TEST", "SYNTH:TE\tST", "SYNTH:\u00a0TEST"]),
    ("timeframe", [None, 5, [], "", "1m", "1d", "60m", "5M", " 5m"]),
    ("source", [None, 123, "", " \t", " fixture", "fixture "]),
])
def test_invalid_bar_metadata_is_rejected(api, field, values):
    for value in values:
        with pytest.raises(ValueError):
            make_bar(api, **{field: value})


@pytest.mark.parametrize("frame,minutes", [("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60), ("4h", 240)])
def test_supported_frames_require_exact_elapsed_duration(api, frame, minutes):
    close = START + timedelta(minutes=minutes)
    bar = make_bar(api, timeframe=frame, closed_at=close, available_at=close)
    assert select(api, [bar], timeframe=frame, decision_time=close).blocker is None
    for delta in (-1, 1):
        with pytest.raises(ValueError):
            replace(bar, closed_at=close + timedelta(microseconds=delta), available_at=close + timedelta(seconds=1))


@pytest.mark.parametrize("field", ["opened_at", "closed_at", "available_at"])
@pytest.mark.parametrize("value", [None, "2026-09-09T12:00:00Z", START.replace(tzinfo=None)])
def test_bar_times_must_be_aware_datetimes(api, field, value):
    with pytest.raises(ValueError):
        make_bar(api, **{field: value})


def test_availability_cannot_precede_close(api):
    with pytest.raises(ValueError):
        make_bar(api, available_at=START + timedelta(minutes=5, microseconds=-1))


def test_utc_normalization_precedes_dst_fold_duration_and_order_checks(api):
    ny = ZoneInfo("America/New_York")
    bar = make_bar(
        api, opened_at=datetime(2026, 11, 1, 1, 55, tzinfo=ny, fold=0),
        closed_at=datetime(2026, 11, 1, 1, 0, tzinfo=ny, fold=1),
        available_at=datetime(2026, 11, 1, 1, 1, tzinfo=ny, fold=1),
    )
    assert bar.opened_at == datetime(2026, 11, 1, 5, 55, tzinfo=timezone.utc)
    assert bar.closed_at == datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
    assert bar.available_at == datetime(2026, 11, 1, 6, 1, tzinfo=timezone.utc)
    assert all(getattr(bar, name).tzinfo is timezone.utc for name in ("opened_at", "closed_at", "available_at"))
    window = select(api, [bar], history_start=datetime(2026, 11, 1, 1, 55, tzinfo=ny, fold=0), decision_time=datetime(2026, 11, 1, 1, 1, tzinfo=ny, fold=1))
    assert window.blocker is None
    assert window.history_start.tzinfo is timezone.utc
    assert window.decision_time == datetime(2026, 11, 1, 6, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        replace(bar, available_at=datetime(2026, 11, 1, 1, 59, tzinfo=ny, fold=0))


@pytest.mark.parametrize("minute,microseconds,expected_count,blocker", [(10, 0, 1, None), (10, 1, 1, "STALE"), (11, 0, 2, None)])
def test_literal_delayed_bar_and_exact_freshness_boundary(api, minute, microseconds, expected_count, blocker):
    first = make_bar(api)
    delayed = make_bar(api, 5, available_at=START + timedelta(minutes=11))
    window = select(api, [first, delayed], decision_time=START + timedelta(minutes=minute, microseconds=microseconds))
    assert window.bars == (first, delayed)[:expected_count]
    assert window.blocker == blocker


def test_future_close_and_availability_are_excluded_and_equality_is_included(api):
    first, second = make_bar(api), make_bar(api, 5)
    future_close = make_bar(api, 10)
    assert select(api, [first, second, future_close]).bars == (first, second)
    assert select(api, [first], decision_time=first.closed_at).bars == (first,)
    assert select(api, [second], decision_time=second.closed_at - timedelta(microseconds=1)).blocker == "NO_HISTORY"


def test_history_start_excludes_older_bars_without_mutating_caller_order(api):
    first, second, older = make_bar(api), make_bar(api, 5), make_bar(api, -5)
    inputs = [second, older, first]
    window = select(api, inputs)
    assert window.bars == (first, second)
    assert inputs == [second, older, first]
    inputs.clear()
    assert window.bars == (first, second)
    assert window.instrument == "SYNTH:TEST"
    assert window.timeframe == "5m"
    assert window.max_age_seconds == 300
    assert window.blocker is None


def test_generator_input_is_sorted_deterministically(api):
    first, second = make_bar(api), make_bar(api, 5)
    assert select(api, (bar for bar in [second, first])) == select(api, [first, second])


@pytest.mark.parametrize("kind", ["empty", "old", "future", "delayed"])
def test_no_eligible_bars_means_no_history(api, kind):
    inputs = {"empty": [], "old": [make_bar(api, -5)], "future": [make_bar(api, 10)], "delayed": [make_bar(api, available_at=START + timedelta(hours=1))]}
    window = select(api, inputs[kind])
    assert window.bars == ()
    assert window.blocker == "NO_HISTORY"


def test_missing_anchor_precedes_gap_and_staleness(api):
    assert select(api, [make_bar(api, 5), make_bar(api, 15)], decision_time=START + timedelta(hours=1)).blocker == "HISTORY_INCOMPLETE"


def test_history_start_inside_bar_does_not_round_to_next_open(api):
    assert select(api, [make_bar(api), make_bar(api, 5)], history_start=START + timedelta(seconds=1)).blocker == "HISTORY_INCOMPLETE"


@pytest.mark.parametrize("second_minute", [4, 10, 2880])
def test_gap_overlap_and_weekend_are_not_compressed_and_precede_staleness(api, second_minute):
    first, second = make_bar(api), make_bar(api, second_minute)
    window = select(api, [first, second], decision_time=START + timedelta(days=3))
    assert window.bars == (first, second)
    assert window.blocker == "HISTORY_GAP"


def test_delayed_interior_bar_blocks_until_it_is_available(api):
    first, middle, last = make_bar(api), make_bar(api, 5, available_at=START + timedelta(minutes=20)), make_bar(api, 10)
    assert select(api, [first, middle, last], decision_time=START + timedelta(minutes=15)).blocker == "HISTORY_GAP"
    recovered = select(api, [first, middle, last], decision_time=START + timedelta(minutes=20))
    assert recovered.bars == (first, middle, last)
    assert recovered.blocker is None


@pytest.mark.parametrize("field,value", [("instrument", "synth:TEST"), ("instrument", "OTHER:TEST"), ("timeframe", "15m")])
def test_exact_identity_mismatch_is_rejected_even_outside_window(api, field, value):
    bar = make_bar(api, -5)
    with pytest.raises(ValueError):
        select(api, [bar], **{field: value})


@pytest.mark.parametrize("revision", [False, True])
@pytest.mark.parametrize("minute", [-5, 0, 10])
def test_duplicate_opens_and_revisions_are_rejected_before_filtering(api, revision, minute):
    bar = make_bar(api, minute)
    other = replace(bar, close=101, source="synthetic:revision", available_at=START + timedelta(days=1)) if revision else bar
    with pytest.raises(ValueError):
        select(api, [bar, other])


def test_same_instant_in_different_timezones_is_duplicate(api):
    first = make_bar(api)
    other = replace(first, opened_at=first.opened_at.astimezone(timezone(timedelta(hours=3))))
    with pytest.raises(ValueError):
        select(api, [first, other])


@pytest.mark.parametrize("value", [None, {}, "bar", 1, True, object()])
def test_selector_rejects_non_closed_bar_items(api, value):
    with pytest.raises(ValueError):
        select(api, [value])


@pytest.mark.parametrize("field,values", [
    ("instrument", [None, "", "TEST", "SYNTH: TEST", "SYNTH:TEST:EXTRA"]),
    ("timeframe", [None, [], "1m", "60m", " 5m"]),
    ("history_start", [None, "2026-09-09", START.replace(tzinfo=None), START + timedelta(hours=1)]),
    ("decision_time", [None, "2026-09-09", START.replace(tzinfo=None)]),
    ("max_age_seconds", [None, True, False, 0, -1, 300.0, "300", Decimal(300)]),
])
def test_request_validation_applies_even_when_input_is_empty(api, field, values):
    for value in values:
        with pytest.raises(ValueError):
            select(api, **{field: value})


def test_freshness_is_explicit_and_has_no_arbitrary_upper_bound(api):
    assert select(api, [make_bar(api)], max_age_seconds=10**100).blocker is None
    with pytest.raises(TypeError):
        api.select_closed_bars([], instrument="SYNTH:TEST", timeframe="5m", decision_time=START, history_start=START)


def test_contracts_are_frozen_keyword_only_and_require_all_fields(api):
    bar = make_bar(api)
    window = select(api, [bar])
    for record in (bar, window):
        with pytest.raises(FrozenInstanceError):
            record.instrument = "OTHER:TEST"
        values = {field.name: getattr(record, field.name) for field in fields(record)}
        with pytest.raises(TypeError):
            type(record)(*values.values())
        for missing in values:
            with pytest.raises(TypeError):
                type(record)(**{name: value for name, value in values.items() if name != missing})


def test_one_nanosecond_past_freshness_boundary_is_rejected_not_rounded(api):
    last = make_bar(api)
    decision_time = pd.Timestamp(last.closed_at) + pd.Timedelta(seconds=300, nanoseconds=1)
    with pytest.raises(ValueError, match="microsecond"):
        select(api, [last], decision_time=decision_time, max_age_seconds=300)


@pytest.mark.parametrize("field", ["opened_at", "closed_at", "available_at"])
@pytest.mark.parametrize("nanoseconds", [-1, 1, 999])
def test_bar_timestamp_submicrosecond_remainders_are_rejected(api, field, nanoseconds):
    bar = make_bar(api)
    unaligned = pd.Timestamp(getattr(bar, field)) + pd.Timedelta(nanoseconds=nanoseconds)
    with pytest.raises(ValueError, match="microsecond"):
        replace(bar, **{field: unaligned})


@pytest.mark.parametrize("field", ["decision_time", "history_start"])
@pytest.mark.parametrize("nanoseconds", [-1, 1, 999])
def test_request_timestamp_submicrosecond_remainders_are_rejected(api, field, nanoseconds):
    unaligned = pd.Timestamp(START) + pd.Timedelta(nanoseconds=nanoseconds)
    with pytest.raises(ValueError, match="microsecond"):
        select(api, **{field: unaligned})


def test_equal_submicrosecond_offsets_cannot_hide_in_exact_bar_duration(api):
    offset = pd.Timedelta(nanoseconds=1)
    with pytest.raises(ValueError, match="microsecond"):
        make_bar(
            api, opened_at=pd.Timestamp(START) + offset,
            closed_at=pd.Timestamp(START) + pd.Timedelta(minutes=5) + offset,
            available_at=pd.Timestamp(START) + pd.Timedelta(minutes=5) + offset,
        )


@pytest.mark.parametrize("timestamp_class", [pd.Timestamp, type("ResearchDatetime", (datetime,), {})])
@pytest.mark.parametrize("zone", [timezone.utc, timezone(timedelta(hours=3)), ZoneInfo("America/New_York")])
def test_aligned_datetime_subclasses_become_native_utc_without_losing_fields(api, timestamp_class, zone):
    opened = datetime(2026, 11, 1, 5, 55, 17, 123456, tzinfo=timezone.utc)
    closed = datetime(2026, 11, 1, 6, 0, 17, 123456, tzinfo=timezone.utc)
    available = datetime(2026, 11, 1, 6, 1, 18, 654321, tzinfo=timezone.utc)

    def as_subclass(value):
        local = value.astimezone(zone)
        return timestamp_class(
            year=local.year, month=local.month, day=local.day,
            hour=local.hour, minute=local.minute, second=local.second,
            microsecond=local.microsecond, tzinfo=zone, fold=local.fold,
        )

    bar = make_bar(api, opened_at=as_subclass(opened), closed_at=as_subclass(closed), available_at=as_subclass(available))
    window = select(api, [bar], history_start=as_subclass(opened), decision_time=as_subclass(available))
    assert window.blocker is None
    for actual, expected in (
        (bar.opened_at, opened), (bar.closed_at, closed),
        (bar.available_at, available), (window.history_start, opened),
        (window.decision_time, available),
    ):
        assert actual == expected
        assert actual.tzinfo is timezone.utc
        assert type(actual) is datetime

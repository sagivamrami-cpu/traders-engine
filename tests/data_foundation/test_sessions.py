from datetime import UTC, datetime
from pathlib import Path

from trading_system.data_foundation.sessions import load_session_calendar, resolve_session

ROOT = Path(__file__).resolve().parents[2]


def calendar():
    return load_session_calendar(
        ROOT / "configs/data/session-calendar.yaml",
        "us-equities-regular-v1",
    )


def gc_calendar():
    return load_session_calendar(
        ROOT / "configs/data/session-calendar.yaml",
        "cme-globex-metals-research-v1",
    )


def test_open_boundary_is_in_session():
    state = resolve_session(datetime(2026, 8, 28, 13, 30, tzinfo=UTC), calendar())

    assert state.in_session
    assert state.is_open_boundary


def test_close_boundary_is_identified():
    state = resolve_session(datetime(2026, 8, 28, 20, 0, tzinfo=UTC), calendar())

    assert state.in_session
    assert state.is_close_boundary


def test_premarket_is_out_of_session():
    state = resolve_session(datetime(2026, 8, 28, 13, 29, 59, tzinfo=UTC), calendar())

    assert not state.in_session


def test_weekend_is_out_of_session():
    state = resolve_session(datetime(2026, 8, 29, 14, 0, tzinfo=UTC), calendar())

    assert not state.in_session


def test_utc_conversion_keeps_local_session_result():
    state = resolve_session(datetime(2026, 8, 28, 15, 0, tzinfo=UTC), calendar())

    assert state.in_session
    assert state.local_date == "2026-08-28"


def test_gc_globex_sunday_open_rolls_to_monday_trade_date():
    before_open = resolve_session(datetime(2026, 9, 6, 21, 59, 59, tzinfo=UTC), gc_calendar())
    at_open = resolve_session(datetime(2026, 9, 6, 22, 0, tzinfo=UTC), gc_calendar())

    assert not before_open.in_session
    assert at_open.in_session
    assert at_open.is_open_boundary
    assert at_open.local_date == "2026-09-06"
    assert at_open.trade_date == "2026-09-07"


def test_gc_globex_daily_break_is_out_of_session():
    before_break = resolve_session(datetime(2026, 9, 7, 20, 59, 59, tzinfo=UTC), gc_calendar())
    break_start = resolve_session(datetime(2026, 9, 7, 21, 0, tzinfo=UTC), gc_calendar())
    during_break = resolve_session(datetime(2026, 9, 7, 21, 30, tzinfo=UTC), gc_calendar())
    reopen = resolve_session(datetime(2026, 9, 7, 22, 0, tzinfo=UTC), gc_calendar())

    assert before_break.in_session
    assert not break_start.in_session
    assert break_start.is_close_boundary
    assert not during_break.in_session
    assert reopen.in_session
    assert reopen.is_open_boundary
    assert reopen.trade_date == "2026-09-08"


def test_gc_globex_weekend_close_starts_after_friday_close():
    before_close = resolve_session(datetime(2026, 9, 11, 20, 59, 59, tzinfo=UTC), gc_calendar())
    friday_close = resolve_session(datetime(2026, 9, 11, 21, 0, tzinfo=UTC), gc_calendar())
    saturday = resolve_session(datetime(2026, 9, 12, 14, 0, tzinfo=UTC), gc_calendar())

    assert before_close.in_session
    assert before_close.trade_date == "2026-09-11"
    assert not friday_close.in_session
    assert friday_close.is_close_boundary
    assert not saturday.in_session

from datetime import UTC, datetime
from pathlib import Path

from trading_system.data_foundation.sessions import load_session_calendar, resolve_session

ROOT = Path(__file__).resolve().parents[2]


def calendar():
    return load_session_calendar(
        ROOT / "configs/data/session-calendar.yaml",
        "us-equities-regular-v1",
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

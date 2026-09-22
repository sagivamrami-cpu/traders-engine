"""Offline ports for source outer-admission time gates."""
from datetime import datetime, timezone

from trading_system.tree_replay.outer_admission_ports import (
    entry_blocked,
    outside_hunting_window,
)


def test_source_time_gates_use_supplied_replay_time_not_wall_clock():
    inside_open = datetime(2026, 1, 5, 0, 30, tzinfo=timezone.utc)  # Monday 02:30 Jerusalem.

    assert outside_hunting_window(inside_open) is None
    assert entry_blocked(inside_open) is None


def test_source_time_gates_preserve_hunting_and_weekend_entry_blocks():
    friday_close = datetime(2026, 1, 2, 21, 30, tzinfo=timezone.utc)  # Friday 23:30 Jerusalem.

    assert "מחוץ לחלון החיפוש" in outside_hunting_window(friday_close)
    assert entry_blocked(friday_close) == "שוק סגור"

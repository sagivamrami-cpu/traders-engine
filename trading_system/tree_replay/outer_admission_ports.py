"""Pure source-pinned outer-admission time gates over supplied replay time.

The functions project `chartdesk/windows.py` at chart-desk commit
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and `floor/marketclock.py` at
trading-floor commit d827dd792cbd1d396b4ee325879c63e57388e07a. They never
read a wall clock, filesystem, network, broker, or source checkout.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from .bars import _utc


_JERUSALEM = ZoneInfo("Asia/Jerusalem")
_HUNT_START_H = 2
_HUNT_END_H = 21
_CLOSE_WEEKDAY = 4
_CLOSE_HOUR = 23
_WARN_MIN_BEFORE = 90


def _now_il(at: datetime) -> datetime:
    return _utc(at, "replay_time").astimezone(_JERUSALEM)


def outside_hunting_window(at: datetime) -> str | None:
    """Return the pinned source hunting-window reason, or ``None`` inside it."""
    local = _now_il(at)
    if _HUNT_START_H <= local.hour < _HUNT_END_H:
        return None
    return f"{local.hour:02d}:00 — מחוץ לחלון החיפוש ({_HUNT_START_H:02d}:00-{_HUNT_END_H:02d}:00)"


def _market_closed(local: datetime) -> bool:
    weekday, hour = local.weekday(), local.hour
    if weekday == _CLOSE_WEEKDAY:
        return hour >= _CLOSE_HOUR
    if weekday in (5, 6):
        return True
    return weekday == 0 and hour < 1


def _minutes_to_close(local: datetime) -> float | None:
    if local.weekday() != _CLOSE_WEEKDAY or _market_closed(local):
        return None
    close = local.replace(hour=_CLOSE_HOUR, minute=0, second=0, microsecond=0)
    return (close - local).total_seconds() / 60.0


def entry_blocked(at: datetime) -> str | None:
    """Return the pinned source new-entry block reason, or ``None``."""
    local = _now_il(at)
    if _market_closed(local):
        return "שוק סגור"
    minutes = _minutes_to_close(local)
    if minutes is not None and minutes <= _WARN_MIN_BEFORE:
        return (f"סגירת שבוע בעוד {minutes:.0f} דק' — לא נפתחות עסקאות חדשות "
                "(גאפ בפתיחה לא ניתן להגנה בסטופ)")
    return None

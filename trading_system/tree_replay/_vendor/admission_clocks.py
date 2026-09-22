from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Jerusalem")


CLOSE_WEEKDAY, CLOSE_HOUR = 4, 23        # Monday=0 ... Friday=4


OPEN_WEEKDAY, OPEN_HOUR = 0, 1           # Monday


def now_il(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError("now must be an aware datetime")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be an aware datetime")
    return now.astimezone(TZ)


def is_closed(now: datetime) -> bool:
    """Is the market inside the weekend window right now?"""
    t = now_il(now)
    wd, hour = t.weekday(), t.hour
    if wd == CLOSE_WEEKDAY:                      # Friday
        return hour >= CLOSE_HOUR
    if wd in (5, 6):                             # Saturday, Sunday
        return True
    if wd == OPEN_WEEKDAY:                       # Monday
        return hour < OPEN_HOUR
    return False


WARN_MIN_BEFORE = 90     # first notice — time to decide, not to react


def minutes_to_close(now: datetime) -> float | None:
    """Minutes until Friday's close, or None when that is not today's story."""
    t = now_il(now)
    if t.weekday() != CLOSE_WEEKDAY or is_closed(t):
        return None
    close = t.replace(hour=CLOSE_HOUR, minute=0, second=0, microsecond=0)
    return (close - t).total_seconds() / 60.0


def entry_blocked(now: datetime) -> str | None:
    """Reason a NEW trade must not be opened now, or None.

    A trade opened an hour before the close cannot reach its target and cannot
    be protected through the weekend, so it is not a trade -- it is a position
    inherited by Monday's gap.
    """
    if is_closed(now):
        return "שוק סגור"
    m = minutes_to_close(now)
    if m is not None and m <= WARN_MIN_BEFORE:
        return (f"סגירת שבוע בעוד {m:.0f} דק' — לא נפתחות עסקאות חדשות "
                "(גאפ בפתיחה לא ניתן להגנה בסטופ)")
    return None


HUNT_START_H = 2


HUNT_END_H = 21


def hunting(now: datetime) -> bool:
    """Is the clock inside his hunting window?"""
    h = now_il(now).hour
    return HUNT_START_H <= h < HUNT_END_H


def outside_reason(now: datetime) -> str | None:
    """Why we are not hunting, or None."""
    if hunting(now):
        return None
    h = now_il(now).hour
    return (f"{h:02d}:00 — מחוץ לחלון החיפוש "
            f"({HUNT_START_H:02d}:00-{HUNT_END_H:02d}:00)")

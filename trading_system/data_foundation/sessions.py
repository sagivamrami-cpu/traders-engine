from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class SessionCalendar:
    calendar_id: str
    version: str
    timezone: str
    regular_open: time
    regular_close: time
    closed_weekdays: tuple[int, ...]
    holidays: tuple[str, ...]
    early_closes: tuple[str, ...]


@dataclass(frozen=True)
class SessionState:
    session_id: str
    local_date: str
    in_session: bool
    is_open_boundary: bool
    is_close_boundary: bool


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def load_session_calendar(path: Path, calendar_id: str) -> SessionCalendar:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    calendar = data["calendars"][calendar_id]
    return SessionCalendar(
        calendar_id=calendar_id,
        version=data["version"],
        timezone=calendar["timezone"],
        regular_open=_parse_time(calendar["regular_session"]["open"]),
        regular_close=_parse_time(calendar["regular_session"]["close"]),
        closed_weekdays=tuple(calendar["closed_weekdays"]),
        holidays=tuple(calendar["holidays"]),
        early_closes=tuple(calendar["early_closes"]),
    )


def resolve_session(timestamp_utc: datetime, calendar: SessionCalendar) -> SessionState:
    if timestamp_utc.tzinfo is None:
        raise ValueError("timestamp_utc must be timezone-aware")
    local = timestamp_utc.astimezone(ZoneInfo(calendar.timezone))
    local_date = local.date().isoformat()
    local_time = local.time().replace(tzinfo=None)
    closed = local.weekday() in calendar.closed_weekdays or local_date in calendar.holidays
    in_regular_hours = calendar.regular_open <= local_time <= calendar.regular_close
    return SessionState(
        session_id=f"{calendar.calendar_id}:{local_date}",
        local_date=local_date,
        in_session=(not closed) and in_regular_hours,
        is_open_boundary=(not closed) and local_time == calendar.regular_open,
        is_close_boundary=(not closed) and local_time == calendar.regular_close,
    )

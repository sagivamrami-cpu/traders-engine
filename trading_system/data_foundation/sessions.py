from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class SessionCalendar:
    calendar_id: str
    version: str
    timezone: str
    session_model: str
    regular_open: time
    regular_close: time
    closed_weekdays: tuple[int, ...]
    holidays: tuple[str, ...]
    early_closes: tuple[str, ...]
    daily_break_start: time | None = None
    daily_break_end: time | None = None


@dataclass(frozen=True)
class SessionState:
    session_id: str
    local_date: str
    trade_date: str
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
        session_model=calendar.get("session_model", "regular_intraday"),
        regular_open=_parse_time(calendar["regular_session"]["open"]),
        regular_close=_parse_time(calendar["regular_session"]["close"]),
        closed_weekdays=tuple(calendar["closed_weekdays"]),
        holidays=tuple(calendar["holidays"]),
        early_closes=tuple(calendar["early_closes"]),
        daily_break_start=(
            _parse_time(calendar["regular_session"]["daily_break_start"])
            if "daily_break_start" in calendar["regular_session"]
            else None
        ),
        daily_break_end=(
            _parse_time(calendar["regular_session"]["daily_break_end"])
            if "daily_break_end" in calendar["regular_session"]
            else None
        ),
    )


def _next_date(local: datetime) -> str:
    return (local.date() + timedelta(days=1)).isoformat()


def _resolve_cme_globex_daily_break(local: datetime, calendar: SessionCalendar) -> SessionState:
    local_date = local.date().isoformat()
    local_time = local.time().replace(tzinfo=None)
    weekday = local.weekday()
    if calendar.daily_break_start is None or calendar.daily_break_end is None:
        raise ValueError("cme_globex_daily_break calendars require daily break times")

    in_session = False
    trade_date = local_date
    if local_date not in calendar.holidays:
        if weekday == 6:
            in_session = local_time >= calendar.regular_open
            trade_date = _next_date(local) if in_session else local_date
        elif 0 <= weekday <= 3:
            if local_time < calendar.daily_break_start:
                in_session = True
                trade_date = local_date
            elif local_time >= calendar.daily_break_end:
                in_session = True
                trade_date = _next_date(local)
        elif weekday == 4 and local_time < calendar.daily_break_start:
            in_session = True
            trade_date = local_date

    is_open_boundary = (
        local_time == calendar.regular_open
        and weekday in (6, 0, 1, 2, 3)
        and local_date not in calendar.holidays
    )
    is_close_boundary = (
        local_time == calendar.regular_close
        and weekday in (0, 1, 2, 3, 4)
        and local_date not in calendar.holidays
    )
    return SessionState(
        session_id=f"{calendar.calendar_id}:{trade_date}",
        local_date=local_date,
        trade_date=trade_date,
        in_session=in_session,
        is_open_boundary=is_open_boundary,
        is_close_boundary=is_close_boundary,
    )


def resolve_session(timestamp_utc: datetime, calendar: SessionCalendar) -> SessionState:
    if timestamp_utc.tzinfo is None:
        raise ValueError("timestamp_utc must be timezone-aware")
    local = timestamp_utc.astimezone(ZoneInfo(calendar.timezone))
    if calendar.session_model == "cme_globex_daily_break":
        return _resolve_cme_globex_daily_break(local, calendar)

    local_date = local.date().isoformat()
    local_time = local.time().replace(tzinfo=None)
    closed = local.weekday() in calendar.closed_weekdays or local_date in calendar.holidays
    in_regular_hours = calendar.regular_open <= local_time <= calendar.regular_close
    return SessionState(
        session_id=f"{calendar.calendar_id}:{local_date}",
        local_date=local_date,
        trade_date=local_date,
        in_session=(not closed) and in_regular_hours,
        is_open_boundary=(not closed) and local_time == calendar.regular_open,
        is_close_boundary=(not closed) and local_time == calendar.regular_close,
    )

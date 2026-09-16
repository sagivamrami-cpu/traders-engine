"""Explicit research session evidence, never verified historical execution truth.

Coverage and open intervals are half-open. Empty intervals declare closed
coverage; they do not describe unknown coverage. Publication evidence is supplied
by the caller and may precede or follow the period to which a schedule applies.
"""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, time, timedelta
from hashlib import sha256
import json

from trading_system.data_foundation import sessions
from trading_system.data_foundation.sessions import SessionCalendar

from .bars import _utc, _validate_identity


def _validate_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be a nonempty trimmed string")


@dataclass(frozen=True, kw_only=True)
class SessionInterval:
    """An explicitly open half-open interval [opened_at, closed_at)."""

    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        for field in ("opened_at", "closed_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.opened_at >= self.closed_at:
            raise ValueError("opened_at must precede closed_at")


@dataclass(frozen=True, kw_only=True)
class SessionSchedule:
    """Immutable supplied evidence with sorted, disjoint, nonadjacent intervals."""

    instrument: str
    calendar_id: str
    version: str
    coverage_start: datetime
    coverage_end: datetime
    available_at: datetime
    source: str
    intervals: tuple[SessionInterval, ...]

    def __post_init__(self) -> None:
        _validate_identity(self.instrument, "5m")
        for field in ("calendar_id", "version", "source"):
            _validate_text(getattr(self, field), field)
        for field in ("coverage_start", "coverage_end", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.coverage_start >= self.coverage_end:
            raise ValueError("coverage_start must precede coverage_end")
        if not isinstance(self.intervals, tuple) or any(
            not isinstance(item, SessionInterval) for item in self.intervals
        ):
            raise ValueError("intervals must be a tuple of SessionInterval inputs")

        canonical: list[SessionInterval] = []
        for item in sorted(self.intervals, key=lambda item: item.opened_at):
            if item.opened_at < self.coverage_start or item.closed_at > self.coverage_end:
                raise ValueError("every interval must lie inside schedule coverage")
            if canonical:
                previous = canonical[-1]
                if item.opened_at < previous.closed_at:
                    raise ValueError("overlapping or duplicate intervals are unsupported")
                if item.opened_at == previous.closed_at:
                    canonical[-1] = SessionInterval(
                        opened_at=previous.opened_at, closed_at=item.closed_at,
                    )
                    continue
            canonical.append(item)
        object.__setattr__(self, "intervals", tuple(canonical))


def schedule_from_research_calendar(
    calendar: SessionCalendar, *, instrument: str, coverage_start: datetime,
    coverage_end: datetime, available_at: datetime, source: str,
) -> SessionSchedule:
    """Resolve only the registered normal-hours template into explicit minutes.

    No calendar is loaded here. Holidays, early closes and changed templates are
    rejected. The caller binds the instrument; this establishes no GC/CFD
    equivalence. Current resolver/timezone rules are research inputs, not proof
    of historical truth. Exact returned intervals can be fingerprinted by users.

    Provenance hashes all calendar dataclass fields as sorted compact JSON,
    with times encoded by ISO format and tuples encoded as JSON arrays.
    """
    if type(calendar) is not SessionCalendar:
        raise ValueError("calendar must be a supplied SessionCalendar")
    template = {
        "calendar_id": "cme-globex-metals-research-v1",
        "timezone": "America/Chicago",
        "session_model": "cme_globex_daily_break",
        "regular_open": time(17),
        "regular_close": time(16),
        "daily_break_start": time(16),
        "daily_break_end": time(17),
        "closed_weekdays": (5,),
        "holidays": (),
        "early_closes": (),
    }
    for field, expected in template.items():
        actual = getattr(calendar, field)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"unsupported research calendar field: {field}")
        # Equality hides float weekdays, time.fold and date-dependent tzinfo.
        if isinstance(actual, time) and (actual.tzinfo is not None or actual.fold != expected.fold):
            raise ValueError(f"unsupported research calendar field: {field}")
        if field == "closed_weekdays" and any(type(day) is not int for day in actual):
            raise ValueError("closed_weekdays must contain exact integers")
    _validate_text(calendar.version, "version")

    # Validate caller evidence before resolving any minutes or decorating source.
    schedule = SessionSchedule(
        instrument=instrument, calendar_id=calendar.calendar_id,
        version=calendar.version, coverage_start=coverage_start,
        coverage_end=coverage_end, available_at=available_at,
        source=source, intervals=(),
    )
    for field in ("coverage_start", "coverage_end"):
        value = getattr(schedule, field)
        if value.second or value.microsecond:
            raise ValueError(f"{field} must be a whole-minute UTC endpoint")

    intervals: list[SessionInterval] = []
    opened_at = None
    minute = schedule.coverage_start
    while minute < schedule.coverage_end:
        if sessions.resolve_session(minute, calendar).in_session:
            if opened_at is None:
                opened_at = minute
        elif opened_at is not None:
            intervals.append(SessionInterval(opened_at=opened_at, closed_at=minute))
            opened_at = None
        minute += timedelta(minutes=1)
    if opened_at is not None:
        intervals.append(SessionInterval(opened_at=opened_at, closed_at=schedule.coverage_end))

    calendar_fields = {
        field: value.isoformat() if isinstance(value, time) else value
        for field, value in asdict(calendar).items()
    }
    digest = sha256(json.dumps(
        calendar_fields, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    return replace(
        schedule, intervals=tuple(intervals),
        source=f"{source}; calendar_sha256={digest}; RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH",
    )

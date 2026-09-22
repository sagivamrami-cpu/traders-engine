"""Explicit closed-bar contracts for offline as-of research.

Only fixed-duration, contiguous histories are supported. Metadata validation is
not proof of historical availability; callers must supply that evidence.
Timestamps must be microsecond-exact; finer precision is rejected, never rounded.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite


_DURATIONS = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


def _validate_identity(instrument: str, timeframe: str) -> None:
    if (
        not isinstance(instrument, str)
        or instrument.count(":") != 1
        or not all(instrument.split(":"))
        or any(character.isspace() for character in instrument)
    ):
        raise ValueError("instrument must be an exact non-whitespace venue:symbol")
    if not isinstance(timeframe, str) or timeframe not in _DURATIONS:
        raise ValueError("timeframe must be 5m, 15m, 30m, 1h or 4h")


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    # pandas Timestamp is a datetime subclass with a nanosecond remainder.
    # Check before conversion so no finer input precision can disappear.
    if getattr(value, "nanosecond", 0) != 0:
        raise ValueError(f"{field} must be microsecond-exact")
    utc = value.astimezone(timezone.utc)
    native = datetime(
        utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second,
        utc.microsecond, tzinfo=timezone.utc,
    )
    if utc != native:
        raise ValueError(f"{field} must be microsecond-exact")
    return native


def _number(value: float, field: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{field} must be a native int or float, not bool")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} exceeds finite float range") from exc
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


@dataclass(frozen=True, kw_only=True)
class ClosedBar:
    """A completed observation, with explicit source and publication time."""

    instrument: str
    timeframe: str
    opened_at: datetime
    closed_at: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source: str

    def __post_init__(self) -> None:
        _validate_identity(self.instrument, self.timeframe)
        if not isinstance(self.source, str) or not self.source or self.source != self.source.strip():
            raise ValueError("source must be a nonempty trimmed string")
        for field in ("opened_at", "closed_at", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.closed_at - self.opened_at != _DURATIONS[self.timeframe]:
            raise ValueError("bar elapsed duration must match timeframe exactly")
        if self.available_at < self.closed_at:
            raise ValueError("available_at cannot precede closed_at")
        for field in ("open", "high", "low", "close"):
            value = _number(getattr(self, field), field)
            if value <= 0:
                raise ValueError(f"{field} must be positive")
            object.__setattr__(self, field, value)
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("open and close must lie between low and high")
        if self.volume is not None:
            volume = _number(self.volume, "volume")
            if volume < 0:
                raise ValueError("volume must be nonnegative or None")
            object.__setattr__(self, "volume", volume)


@dataclass(frozen=True, kw_only=True)
class BarWindow:
    """Selector result; a non-null blocker forbids using it as usable history."""

    instrument: str
    timeframe: str
    decision_time: datetime
    history_start: datetime
    max_age_seconds: int
    bars: tuple[ClosedBar, ...]
    blocker: str | None


def select_closed_bars(
    bars: Iterable[ClosedBar], *, instrument: str, timeframe: str,
    decision_time: datetime, history_start: datetime, max_age_seconds: int,
) -> BarWindow:
    """Validate every input, then select closed and available bars as of T.

    Duplicate opens (including revisions) and mixed identities are invalid even
    outside the selected window. No calendar, resampling or revision policy is
    inferred. Blocked results retain selected bars for diagnostics only.
    """
    _validate_identity(instrument, timeframe)
    decision_time = _utc(decision_time, "decision_time")
    history_start = _utc(history_start, "history_start")
    if history_start > decision_time:
        raise ValueError("history_start cannot be after decision_time")
    if type(max_age_seconds) is not int or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be an explicit positive integer")

    selected = []
    seen_opens = set()
    for bar in bars:
        if not isinstance(bar, ClosedBar):
            raise ValueError("bars must contain only ClosedBar inputs")
        if bar.instrument != instrument or bar.timeframe != timeframe:
            raise ValueError("every bar must match the exact instrument and timeframe")
        if bar.opened_at in seen_opens:
            raise ValueError("duplicate bar opens and revisions are unsupported")
        seen_opens.add(bar.opened_at)
        if (
            bar.opened_at >= history_start
            and bar.closed_at <= decision_time
            and bar.available_at <= decision_time
        ):
            selected.append(bar)
    selected.sort(key=lambda bar: bar.opened_at)

    blocker = None
    if not selected:
        blocker = "NO_HISTORY"
    elif selected[0].opened_at != history_start:
        blocker = "HISTORY_INCOMPLETE"
    elif any(previous.closed_at != following.opened_at for previous, following in zip(selected, selected[1:])):
        blocker = "HISTORY_GAP"
    else:
        age = decision_time - selected[-1].closed_at
        # Integer arithmetic preserves microseconds even over long histories,
        # and accepts explicit budgets larger than timedelta's representable range.
        age_microseconds = (age.days * 86400 + age.seconds) * 1_000_000 + age.microseconds
        if age_microseconds > max_age_seconds * 1_000_000:
            blocker = "STALE"

    return BarWindow(
        instrument=instrument, timeframe=timeframe, decision_time=decision_time,
        history_start=history_start, max_age_seconds=max_age_seconds,
        bars=tuple(selected), blocker=blocker,
    )

"""Causal daily-period OHLC from explicit boundaries and published closed bars.

Period boundaries and calendars are supplied evidence, not inferred broker rules.
The supported observation precision is a lower-timeframe close, not an open-only
tick or a partly observed lower bar. No full level map or replay is certified.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math

from .bars import ClosedBar, _DURATIONS, _utc, _validate_identity
from .calendar import SessionSchedule, _validate_text


VERSION = "closed-lower-bars-daily-period-v1"


@dataclass(frozen=True, kw_only=True)
class DailyPeriod:
    """Explicit broker-day identity; DST days need not have24 elapsed hours."""
    instrument: str
    period_id: str
    opened_at: datetime
    closed_at: datetime
    available_at: datetime
    source: str
    version: str

    def __post_init__(self):
        _validate_identity(self.instrument, "5m")
        for name in ("period_id", "source", "version"):
            _validate_text(getattr(self, name), name)
        for name in ("opened_at", "closed_at", "available_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.opened_at >= self.closed_at:
            raise ValueError("period opened_at must precede closed_at")


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=lambda time: time.isoformat().replace("+00:00", "Z"))


def aggregate_daily_asof(bars, *, period, decision_time, base_timeframe,
                         session_schedule) -> dict:
    """Require all scheduled bars up to min(T, period end), published by T.

    A late final bar can be consumed after period end without pretending it was
    known at end. No wall-clock staleness policy erases a completed historical
    day. Any unresolved trading fragment prevents publishing aggregate prices.
    """
    if not isinstance(period, DailyPeriod):
        raise ValueError("period must be a DailyPeriod")
    if not isinstance(session_schedule, SessionSchedule):
        raise ValueError("session_schedule must be a SessionSchedule")
    _validate_identity(period.instrument, base_timeframe)
    if session_schedule.instrument != period.instrument:
        raise ValueError("calendar must match the exact period instrument")
    decision_time = _utc(decision_time, "decision_time")
    if decision_time < period.opened_at:
        raise ValueError("decision_time cannot precede period open")
    cutoff = min(decision_time, period.closed_at)
    step = _DURATIONS[base_timeframe]
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if any((time-epoch) % step for time in (period.opened_at, period.closed_at, cutoff)):
        raise ValueError("period boundaries and observation cutoff must align to base grid")

    present, seen = {}, set()
    for bar in bars:
        if not isinstance(bar, ClosedBar):
            raise ValueError("bars must contain ClosedBar inputs")
        if bar.instrument != period.instrument or bar.timeframe != base_timeframe:
            raise ValueError("all bars must match exact instrument and base timeframe")
        if bar.opened_at in seen:
            raise ValueError("duplicate bar opens and revisions are unsupported")
        seen.add(bar.opened_at)
        if (period.opened_at <= bar.opened_at and bar.closed_at <= cutoff
                and bar.available_at <= decision_time):
            # Closure-only bars remain present for exclusion diagnostics; any
            # overlap with an active session still requires grid alignment.
            overlaps_session = any(
                bar.opened_at < interval.closed_at and interval.opened_at < bar.closed_at
                for interval in session_schedule.intervals)
            if overlaps_session and (bar.opened_at-epoch) % step:
                raise ValueError("selected bar opens must align to base grid")
            present[bar.opened_at] = bar

    schedule = session_schedule
    expected = []
    blocker = None
    if period.available_at > decision_time:
        blocker = "PERIOD_UNAVAILABLE"
    elif schedule.available_at > decision_time:
        blocker = "CALENDAR_UNAVAILABLE"
    elif schedule.coverage_start > period.opened_at or schedule.coverage_end < cutoff:
        blocker = "CALENDAR_COVERAGE"
    else:
        for interval in schedule.intervals:
            start = max(interval.opened_at, period.opened_at)
            end = min(interval.closed_at, cutoff)
            if start >= end:
                continue
            if (start-epoch) % step or (end-epoch) % step:
                blocker = "PERIOD_GRID_UNRESOLVED"
                expected = []
                break
            while start < end:
                expected.append(start)
                start += step

    selected = tuple(present[time] for time in expected if time in present)
    missing = tuple(time for time in expected if time not in present)
    if blocker is None:
        if not expected:
            blocker = "NO_EXPECTED_BARS"
        elif expected[0] not in present:
            blocker = "HISTORY_INCOMPLETE"
        elif missing:
            blocker = "HISTORY_GAP"
    outside = len(present) - len(selected) if blocker not in (
        "PERIOD_UNAVAILABLE", "CALENDAR_UNAVAILABLE", "CALENDAR_COVERAGE",
        "PERIOD_GRID_UNRESOLVED") else 0
    evidence = dict(version=VERSION, period=asdict(period), calendar=asdict(schedule),
                    base_timeframe=base_timeframe, decision_time=decision_time,
                    bars=[asdict(bar) for bar in selected], expected_bars=len(expected),
                    missing_opens=missing, out_of_session_bars=outside, blocker=blocker)
    result = dict(schema_version="daily-period-asof-v1", calculation_version=VERSION,
                  period=asdict(period), base_timeframe=base_timeframe,
                  decision_time=decision_time, status="BLOCKED", blocker=blocker,
                  ohlcv=None, observed_at=None, available_at=None,
                  expected_bars=len(expected), missing_opens=missing,
                  out_of_session_bars=outside,
                  evaluation_sha256=hashlib.sha256(_encode(evidence).encode()).hexdigest(),
                  ready_for_replay=False, ready_for_training=False)
    if blocker is None:
        volume = None
        if all(bar.volume is not None for bar in selected):
            try:
                volume = math.fsum(bar.volume for bar in selected)
            except OverflowError as exc:
                raise ValueError("aggregate volume overflow") from exc
            if not math.isfinite(volume):
                raise ValueError("aggregate volume must be finite")
        result.update(status="CLOSED" if decision_time >= period.closed_at else "FORMING",
                      ohlcv=dict(open=selected[0].open, high=max(b.high for b in selected),
                                 low=min(b.low for b in selected), close=selected[-1].close,
                                 volume=volume), observed_at=selected[-1].closed_at,
                      available_at=max(period.available_at, schedule.available_at,
                                       *(b.available_at for b in selected)))
    return json.loads(_encode(result))

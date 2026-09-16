"""Opt-in calendar-aware closed-bar selection; supplied schedules are evidence, not approval."""
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json

from .bars import BarWindow, _DURATIONS, select_closed_bars
from .calendar import SessionSchedule


@dataclass(frozen=True, kw_only=True)
class SessionBarWindow(BarWindow):
    schedule_sha256: str
    calendar_available_at: datetime
    expected_bars: int
    missing_opens: tuple[datetime, ...]
    out_of_session_bars: int
    straddling_bars: int


def select_session_bars(bars, *, instrument, timeframe, decision_time,
                        history_start, max_age_seconds, session_schedule) -> SessionBarWindow:
    """Require every expected closed bar across the entire explicitly anchored seed.

    Coverage includes scheduled closures. A bar that overlaps a closure is not
    a complete open-session bar, even when its two endpoints are open. Missing
    expected bars are never compressed away. Freshness is elapsed wall time.
    """
    base = select_closed_bars(bars, instrument=instrument, timeframe=timeframe,
                             decision_time=decision_time, history_start=history_start,
                             max_age_seconds=max_age_seconds)
    if not isinstance(session_schedule, SessionSchedule):
        raise ValueError("session_schedule must be a SessionSchedule")
    schedule = session_schedule
    if schedule.instrument != instrument:
        raise ValueError("schedule must match exact instrument")
    step = _DURATIONS[timeframe]
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if (base.history_start - epoch) % step:
        raise ValueError("history_start must align to the fixed UTC grid")
    if any((b.opened_at - epoch) % step for b in base.bars):
        raise ValueError("selected bar opens must align to the fixed UTC grid")

    encoded = json.dumps(asdict(schedule), sort_keys=True, separators=(",", ":"),
                         default=lambda value: value.isoformat().replace("+00:00", "Z"))
    schedule_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    expected = []
    missing = ()
    selected = base.bars
    outside = straddling = 0

    if schedule.available_at > base.decision_time:
        blocker = "CALENDAR_UNAVAILABLE"
    elif schedule.coverage_start > base.history_start or schedule.coverage_end < base.decision_time:
        blocker = "CALENDAR_COVERAGE"
    else:
        intervals = schedule.intervals
        openings = tuple(i.opened_at for i in intervals)

        def membership(start, end):
            index = bisect_right(openings, start) - 1
            if index >= 0:
                interval = intervals[index]
                if end <= interval.closed_at:
                    return "OPEN"
                if start < interval.closed_at:
                    return "STRADDLE"
            if index + 1 < len(intervals) and intervals[index + 1].opened_at < end:
                return "STRADDLE"
            return "CLOSED"

        start = base.history_start
        # Difference comparison avoids overflowing datetime at the upper boundary.
        while base.decision_time - start >= step:
            end = start + step
            if membership(start, end) == "OPEN":
                expected.append(start)
            start = end
        present = {}
        for b in base.bars:
            kind = membership(b.opened_at, b.closed_at)
            if kind == "OPEN":
                present[b.opened_at] = b
            elif kind == "STRADDLE":
                straddling += 1
            else:
                outside += 1
        selected = tuple(present[t] for t in expected if t in present)
        missing = tuple(t for t in expected if t not in present)
        if not expected:
            blocker = "NO_EXPECTED_BARS"
        elif expected[0] not in present:
            blocker = "HISTORY_INCOMPLETE"
        elif missing:
            blocker = "HISTORY_GAP"
        elif (base.decision_time - selected[-1].closed_at) // timedelta(microseconds=1) > max_age_seconds * 1_000_000:
            blocker = "STALE"
        else:
            blocker = None

    return SessionBarWindow(
        instrument=instrument, timeframe=timeframe, decision_time=base.decision_time,
        history_start=base.history_start, max_age_seconds=max_age_seconds,
        bars=selected, blocker=blocker, schedule_sha256=schedule_hash,
        calendar_available_at=schedule.available_at, expected_bars=len(expected),
        missing_opens=missing, out_of_session_bars=outside, straddling_bars=straddling,
    )

"""Historical map frames from published closed base bars and supplied grids.

Source labels are not publication times. This builds a known lower-bar prefix,
not an open-only tick, a partial base bar or independently certified market data.
"""
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

from .bars import ClosedBar, _DURATIONS, _utc, _validate_identity
from .calendar import SessionSchedule
from .levels import _text
from .periods import DailyPeriod, _encode, aggregate_daily_asof
from .session_bars import select_session_bars


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
VERSION = "closed-base-frame-v1"


@dataclass(frozen=True, kw_only=True)
class LabeledDailyPeriod:
    period: DailyPeriod
    source_index_at: datetime

    def __post_init__(self):
        if not isinstance(self.period, DailyPeriod):
            raise ValueError("period must be a DailyPeriod")
        object.__setattr__(self, "source_index_at", _utc(self.source_index_at, "source_index_at"))


@dataclass(frozen=True, kw_only=True)
class FrameSpec:
    frame_id: str
    instrument: str
    timeframe: str
    base_timeframe: str
    history_start: datetime
    available_at: datetime
    source: str
    version: str
    bars: tuple[ClosedBar, ...]
    session_schedule: SessionSchedule
    max_age_seconds: int
    grid_anchor: datetime | None = None
    periods: tuple[LabeledDailyPeriod, ...] = ()

    def __post_init__(self):
        _validate_identity(self.instrument, self.base_timeframe)
        if not isinstance(self.timeframe, str) or (self.timeframe != "1d" and self.timeframe not in _DURATIONS):
            raise ValueError("timeframe must be 1d or a supported fixed timeframe")
        for field in ("frame_id", "source", "version"):
            _text(getattr(self, field), field)
        for field in ("history_start", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if type(self.max_age_seconds) is not int or self.max_age_seconds < 0:
            raise ValueError("max_age_seconds must be a native nonnegative integer")
        if not isinstance(self.session_schedule, SessionSchedule):
            raise ValueError("session_schedule must be a SessionSchedule")
        if self.session_schedule.instrument != self.instrument:
            raise ValueError("calendar must match exact frame instrument")
        if type(self.bars) is not tuple or any(not isinstance(b, ClosedBar) for b in self.bars):
            raise ValueError("bars must be a tuple of ClosedBar objects")
        if any(b.instrument != self.instrument or b.timeframe != self.base_timeframe for b in self.bars):
            raise ValueError("all bars must match exact instrument and base timeframe")
        if len({b.opened_at for b in self.bars}) != len(self.bars):
            raise ValueError("duplicate bar opens and revisions are unsupported")
        object.__setattr__(self, "bars", tuple(sorted(self.bars, key=lambda b: b.opened_at)))
        if type(self.periods) is not tuple or any(not isinstance(p, LabeledDailyPeriod) for p in self.periods):
            raise ValueError("periods must be a tuple of LabeledDailyPeriod objects")
        step = _DURATIONS[self.base_timeframe]
        if (self.history_start-EPOCH) % step:
            raise ValueError("history_start must align to the base grid")
        if self.timeframe == "1d":
            if self.grid_anchor is not None or not self.periods:
                raise ValueError("daily frames require explicit periods and no grid_anchor")
            ordered = tuple(sorted(self.periods, key=lambda p: p.period.opened_at))
            if len({p.period.period_id for p in ordered}) != len(ordered):
                raise ValueError("duplicate daily period IDs")
            for i, labeled in enumerate(ordered):
                period = labeled.period
                if period.instrument != self.instrument:
                    raise ValueError("period must match exact frame instrument")
                if any((t-EPOCH) % step for t in (period.opened_at, period.closed_at)):
                    raise ValueError("period boundaries must align to the base grid")
                if i and (ordered[i-1].period.closed_at > period.opened_at or
                          ordered[i-1].source_index_at >= labeled.source_index_at):
                    raise ValueError("periods must be disjoint with strictly increasing source labels")
            object.__setattr__(self, "periods", ordered)
        else:
            if self.periods:
                raise ValueError("intraday frames cannot contain daily periods")
            target = _DURATIONS[self.timeframe]
            if target < step:
                raise ValueError("cannot upsample a coarser base timeframe")
            anchor = _utc(self.grid_anchor, "grid_anchor")
            if (anchor-EPOCH) % step or (self.history_start-anchor) % target:
                raise ValueError("grid_anchor and history_start must align to the explicit grid")
            object.__setattr__(self, "grid_anchor", anchor)


def _stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _daily_rows(spec, decision):
    selected = tuple(p for p in spec.periods
                     if p.period.closed_at > spec.history_start and p.period.opened_at <= decision)
    details = {"periods": [asdict(p) for p in selected], "aggregates": [], "skipped_closed_periods": []}
    if not selected or not (selected[-1].period.opened_at <= decision < selected[-1].period.closed_at):
        return [], "CURRENT_PERIOD_UNCOVERED", details
    if selected[0].period.opened_at != spec.history_start:
        raise ValueError("daily history_start must equal the first selected period open")
    # Every active fragment must have a period owner, including intervals whose
    # bars are absent. Known calendar closures between periods need no fake row.
    for interval in spec.session_schedule.intervals:
        cursor, end = max(interval.opened_at, spec.history_start), min(interval.closed_at, decision)
        if cursor >= end:
            continue
        for labeled in selected:
            period = labeled.period
            if period.closed_at <= cursor:
                continue
            if period.opened_at > cursor:
                break
            cursor = min(end, period.closed_at)
            if cursor == end:
                break
        if cursor < end:
            return [], "PERIOD_SEQUENCE_GAP", details

    openings = tuple(p.period.opened_at for p in selected)
    buckets = [[] for _ in selected]
    for bar in spec.bars:
        if not (spec.history_start <= bar.opened_at and bar.closed_at <= decision and bar.available_at <= decision):
            continue
        i = bisect_right(openings, bar.opened_at)-1
        if i >= 0 and bar.closed_at <= selected[i].period.closed_at:
            buckets[i].append(bar)
    rows = []
    for labeled, bars in zip(selected, buckets):
        period = labeled.period
        observed = aggregate_daily_asof(
            bars, period=period, decision_time=decision,
            base_timeframe=spec.base_timeframe, session_schedule=spec.session_schedule,
        )
        details["aggregates"].append({
            "period_id": period.period_id, "status": observed["status"],
            "blocker": observed["blocker"], "evaluation_sha256": observed["evaluation_sha256"],
        })
        if observed["blocker"] == "NO_EXPECTED_BARS" and decision >= period.closed_at:
            details["skipped_closed_periods"].append(period.period_id)
            continue
        if observed["blocker"] is not None:
            return [], observed["blocker"], details
        rows.append(dict(
            source_index_at=labeled.source_index_at, opened_at=period.opened_at,
            closed_at=period.closed_at, observed_at=_stamp(observed["observed_at"]),
            available_at=max(spec.available_at, _stamp(observed["available_at"])),
            state=observed["status"], **observed["ohlcv"],
        ))
    return rows, None, details


def _intraday_rows(spec, decision):
    step = _DURATIONS[spec.base_timeframe]
    for interval in spec.session_schedule.intervals:
        start, end = max(spec.history_start, interval.opened_at), min(decision, interval.closed_at)
        if start < end and ((start-EPOCH) % step or (end-EPOCH) % step):
            return [], "FRAME_GRID_UNRESOLVED", {}
    window = select_session_bars(
        spec.bars, instrument=spec.instrument, timeframe=spec.base_timeframe,
        decision_time=decision, history_start=spec.history_start,
        # The existing selector requires a positive budget. Its one-second
        # compatibility floor never relaxes this frame's policy: the exact
        # caller budget (including zero) is enforced again on the final rows.
        max_age_seconds=max(1, spec.max_age_seconds), session_schedule=spec.session_schedule,
    )
    details = {"expected_bars": window.expected_bars, "missing_opens": window.missing_opens,
               "out_of_session_bars": window.out_of_session_bars,
               "straddling_bars": window.straddling_bars,
               "bars": [asdict(b) for b in window.bars]}
    if window.blocker:
        return [], window.blocker, details
    target = _DURATIONS[spec.timeframe]
    groups = {}
    for bar in window.bars:
        opened = spec.grid_anchor + ((bar.opened_at-spec.grid_anchor)//target)*target
        groups.setdefault(opened, []).append(bar)
    rows = []
    for opened, bars in groups.items():
        volume = None
        if all(b.volume is not None for b in bars):
            try:
                volume = math.fsum(b.volume for b in bars)
            except OverflowError as exc:
                raise ValueError("frame volume overflow") from exc
            if not math.isfinite(volume):
                raise ValueError("frame volume must be finite")
        try:
            closed = opened+target
        except OverflowError as exc:
            raise ValueError("frame grid close exceeds datetime range") from exc
        rows.append(dict(
            source_index_at=opened, opened_at=opened, closed_at=closed,
            observed_at=bars[-1].closed_at,
            available_at=max(spec.available_at, spec.session_schedule.available_at,
                             *(b.available_at for b in bars)),
            state="CLOSED" if closed <= decision else "FORMING",
            open=bars[0].open, high=max(b.high for b in bars), low=min(b.low for b in bars),
            close=bars[-1].close, volume=volume,
        ))
    return rows, None, details


def build_frame_asof(spec: FrameSpec, *, decision_time: datetime) -> dict:
    """Build the available closed-base prefix, with no implicit day/grid origin."""
    if not isinstance(spec, FrameSpec):
        raise ValueError("spec must be a FrameSpec")
    decision = _utc(decision_time, "decision_time")
    if decision < spec.history_start or (decision-EPOCH) % _DURATIONS[spec.base_timeframe]:
        raise ValueError("decision_time must follow history_start on the base grid")
    calendar = spec.session_schedule
    rows, details = [], {}
    if spec.available_at > decision:
        blocker = "FRAME_METADATA_UNAVAILABLE"
    elif calendar.available_at > decision:
        blocker = "CALENDAR_UNAVAILABLE"
    elif calendar.coverage_start > spec.history_start or calendar.coverage_end < decision:
        blocker = "CALENDAR_COVERAGE"
    else:
        rows, blocker, details = (_daily_rows(spec, decision) if spec.timeframe == "1d"
                                  else _intraday_rows(spec, decision))
        if blocker is None and (decision-rows[-1]["observed_at"]) // timedelta(microseconds=1) > spec.max_age_seconds*1_000_000:
            blocker = "STALE"
            rows = []
    result = dict(
        schema_version="historical-frame-asof-v1", calculation_version=VERSION,
        frame_id=spec.frame_id, instrument=spec.instrument, timeframe=spec.timeframe,
        base_timeframe=spec.base_timeframe, decision_time=decision,
        status="BLOCKED" if blocker else "AVAILABLE", blocker=blocker, rows=rows,
        observed_at=rows[-1]["observed_at"] if rows else None,
        available_at=max(r["available_at"] for r in rows) if rows else None,
        diagnostics=details, ready_for_replay=False, ready_for_training=False,
    )
    evidence = dict(result=result, source=spec.source, version=spec.version,
                    history_start=spec.history_start, metadata_available_at=spec.available_at,
                    grid_anchor=spec.grid_anchor, max_age_seconds=spec.max_age_seconds,
                    calendar=asdict(calendar))
    result["evaluation_sha256"] = hashlib.sha256(_encode(evidence).encode()).hexdigest()
    return json.loads(_encode(result))

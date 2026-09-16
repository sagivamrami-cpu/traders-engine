"""Causal CME:GC flow observations for an OANDA:XAUUSD decision.

This module intentionally exposes no price values or trading action.  It is a
sidecar context that a later, explicitly approved feature/dataset layer may
consume.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math

from .cross_market_flow_policy import CrossMarketFlowPolicy


_MINUTE = timedelta(minutes=1)


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"CROSS_MARKET_{name}")
    return value.astimezone(UTC)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class GcFlowMinute:
    minute_start: datetime
    available_at: datetime
    volume: float
    delta: float
    trades: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "minute_start", _utc(self.minute_start, "MINUTE_START"))
        object.__setattr__(self, "available_at", _utc(self.available_at, "MINUTE_AVAILABLE_AT"))


@dataclass(frozen=True, kw_only=True)
class CrossMarketFlowInput:
    policy: CrossMarketFlowPolicy
    archive_sha256: str
    coverage_start: datetime
    coverage_end: datetime
    minutes: tuple[GcFlowMinute, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy, CrossMarketFlowPolicy):
            raise ValueError("CROSS_MARKET_POLICY")
        if type(self.archive_sha256) is not str:
            raise ValueError("CROSS_MARKET_ARCHIVE")
        object.__setattr__(self, "coverage_start", _utc(self.coverage_start, "COVERAGE_START"))
        object.__setattr__(self, "coverage_end", _utc(self.coverage_end, "COVERAGE_END"))
        if self.coverage_start >= self.coverage_end:
            raise ValueError("CROSS_MARKET_COVERAGE")
        if type(self.minutes) is not tuple or not all(type(item) is GcFlowMinute for item in self.minutes):
            raise ValueError("CROSS_MARKET_MINUTES")


@dataclass(frozen=True, kw_only=True)
class CrossMarketFlowContext:
    status: str
    reason: str | None
    target_instrument: str
    source_instrument: str
    source_dataset: str
    archive_sha256: str
    decision_time: datetime
    window_start: datetime
    observed_at: datetime | None
    available_at: datetime | None
    volume: float | None
    delta: float | None
    trades: float | None

    def __post_init__(self) -> None:
        if self.status not in {"AVAILABLE", "UNAVAILABLE"}:
            raise ValueError("CROSS_MARKET_CONTEXT_STATUS")
        if (self.status == "AVAILABLE") != (self.reason is None):
            raise ValueError("CROSS_MARKET_CONTEXT_REASON")
        object.__setattr__(self, "decision_time", _utc(self.decision_time, "DECISION_TIME"))
        object.__setattr__(self, "window_start", _utc(self.window_start, "WINDOW_START"))
        for field in ("observed_at", "available_at"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _utc(value, field.upper()))
        if self.status == "AVAILABLE":
            if any(value is None for value in (self.observed_at, self.available_at, self.volume, self.delta, self.trades)):
                raise ValueError("CROSS_MARKET_CONTEXT_VALUES")
        elif any(value is not None for value in (self.observed_at, self.available_at, self.volume, self.delta, self.trades)):
            raise ValueError("CROSS_MARKET_CONTEXT_UNAVAILABLE_VALUES")

    def commitment(self) -> dict[str, object]:
        """Return provenance and payload commitment without exposing flow values."""
        private = {
            "status": self.status,
            "reason": self.reason,
            "volume": self.volume,
            "delta": self.delta,
            "trades": self.trades,
        }
        return {
            "schema_version": "cross-market-flow-context-v1",
            "target_instrument": self.target_instrument,
            "source_instrument": self.source_instrument,
            "source_dataset": self.source_dataset,
            "archive_sha256": self.archive_sha256,
            "decision_time": self.decision_time.isoformat(),
            "window_start": self.window_start.isoformat(),
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "status": self.status,
            "reason": self.reason,
            "context_digest": _digest(private),
        }


def _unavailable(source: CrossMarketFlowInput, decision_time: datetime, window_start: datetime, reason: str) -> CrossMarketFlowContext:
    return CrossMarketFlowContext(
        status="UNAVAILABLE", reason=reason,
        target_instrument=source.policy.target_instrument,
        source_instrument=source.policy.source_instrument,
        source_dataset=source.policy.source_dataset,
        archive_sha256=source.archive_sha256,
        decision_time=decision_time, window_start=window_start,
        observed_at=None, available_at=None, volume=None, delta=None, trades=None,
    )


def _expected_starts(window_start: datetime, decision_time: datetime) -> tuple[datetime, ...]:
    current = window_start.replace(second=0, microsecond=0)
    if current < window_start:
        current += _MINUTE
    starts: list[datetime] = []
    while current + _MINUTE <= decision_time:
        starts.append(current)
        current += _MINUTE
    return tuple(starts)


def _aggregate(rows: list[GcFlowMinute], field: str) -> float | None:
    try:
        value = math.fsum(float(getattr(row, field)) for row in rows)
    except OverflowError:
        return None
    return value if math.isfinite(value) else None


def build_cross_market_flow_context(
    source: CrossMarketFlowInput,
    *,
    decision_time: datetime,
    window_start: datetime,
) -> CrossMarketFlowContext:
    """Aggregate one caller-declared closed GC-minute window at decision time."""
    if not isinstance(source, CrossMarketFlowInput):
        raise ValueError("CROSS_MARKET_INPUT")
    decision = _utc(decision_time, "DECISION_TIME")
    start = _utc(window_start, "WINDOW_START")
    if start >= decision:
        raise ValueError("CROSS_MARKET_WINDOW")
    policy = source.policy
    if (
        policy.target_instrument != "OANDA:XAUUSD"
        or policy.source_instrument != "CME:GC"
        or policy.source_dataset != "DATABENTO/GLBX.MDP3"
        or source.archive_sha256 != policy.archive_sha256
    ):
        return _unavailable(source, decision, start, "GC_SOURCE_IDENTITY")
    expected = _expected_starts(start, decision)
    if not expected:
        return _unavailable(source, decision, start, "GC_NO_CLOSED_MINUTE")
    if expected[0] < source.coverage_start or expected[-1] + _MINUTE > source.coverage_end:
        return _unavailable(source, decision, start, "GC_COVERAGE")
    if any(policy.damaged_start <= minute_start < policy.damaged_end for minute_start in expected):
        return _unavailable(source, decision, start, "GC_DAMAGED_ERA")
    rows = {item.minute_start: item for item in source.minutes}
    if len(rows) != len(source.minutes):
        return _unavailable(source, decision, start, "GC_MINUTE_DUPLICATE")
    if tuple(sorted(rows)) != tuple(item.minute_start for item in source.minutes):
        return _unavailable(source, decision, start, "GC_MINUTE_ORDER")
    selected: list[GcFlowMinute] = []
    for minute_start in expected:
        row = rows.get(minute_start)
        if row is None:
            return _unavailable(source, decision, start, "GC_MINUTE_GAP")
        if not all(math.isfinite(float(value)) for value in (row.volume, row.delta, row.trades)):
            return _unavailable(source, decision, start, "GC_NONFINITE_VALUE")
        if row.available_at > decision:
            return _unavailable(source, decision, start, "GC_MINUTE_LATE")
        selected.append(row)
    volume = _aggregate(selected, "volume")
    delta = _aggregate(selected, "delta")
    trades = _aggregate(selected, "trades")
    if any(value is None for value in (volume, delta, trades)):
        return _unavailable(source, decision, start, "GC_AGGREGATE_NONFINITE")
    return CrossMarketFlowContext(
        status="AVAILABLE", reason=None,
        target_instrument=policy.target_instrument,
        source_instrument=policy.source_instrument,
        source_dataset=policy.source_dataset,
        archive_sha256=source.archive_sha256,
        decision_time=decision, window_start=start,
        observed_at=selected[-1].minute_start + _MINUTE,
        available_at=max(row.available_at for row in selected),
        volume=volume,
        delta=delta,
        trades=trades,
    )

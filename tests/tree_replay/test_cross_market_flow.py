from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import math

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "configs/data/xauusd-gc-crossmarket-order-flow-context.yaml"
T = datetime(2026, 1, 2, 9, 35, tzinfo=UTC)


def at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minute(value: str, *, available_at: str | None = None, volume: float = 10.0, delta: float = 2.0, trades: float = 3.0):
    from trading_system.tree_replay.cross_market_flow import GcFlowMinute

    started = at(value)
    return GcFlowMinute(
        minute_start=started,
        available_at=at(available_at) if available_at else started + timedelta(minutes=1),
        volume=volume,
        delta=delta,
        trades=trades,
    )


def source_with(*minutes, target: str = "OANDA:XAUUSD", source: str = "CME:GC", coverage_start: datetime | None = None, coverage_end: datetime | None = None):
    from trading_system.tree_replay.cross_market_flow import CrossMarketFlowInput
    from trading_system.tree_replay.cross_market_flow_policy import CrossMarketFlowPolicy

    policy = CrossMarketFlowPolicy.load(POLICY)
    if target != policy.target_instrument or source != policy.source_instrument:
        policy = policy.__class__(
            target_instrument=target,
            source_instrument=source,
            source_dataset=policy.source_dataset,
            archive_sha256=policy.archive_sha256,
            selected_member=policy.selected_member,
            allowed_columns=policy.allowed_columns,
            damaged_start=policy.damaged_start,
            damaged_end=policy.damaged_end,
        )
    starts = [item.minute_start for item in minutes]
    return CrossMarketFlowInput(
        policy=policy,
        archive_sha256=policy.archive_sha256,
        coverage_start=coverage_start or min(starts),
        coverage_end=coverage_end or max(starts) + timedelta(minutes=1),
        minutes=tuple(minutes),
    )


def context(source, *, decision_time: datetime = T, window_start: datetime | None = None):
    from trading_system.tree_replay.cross_market_flow import build_cross_market_flow_context

    return build_cross_market_flow_context(
        source,
        decision_time=decision_time,
        window_start=window_start or decision_time - timedelta(minutes=2),
    )


def test_minute_is_not_eligible_until_its_end_and_availability_are_at_or_before_decision_time():
    source = source_with(minute("2026-01-02T09:30:00Z"))

    early = context(source, decision_time=at("2026-01-02T09:30:59Z"), window_start=at("2026-01-02T09:30:00Z"))
    on_end = context(source, decision_time=at("2026-01-02T09:31:00Z"), window_start=at("2026-01-02T09:30:00Z"))

    assert (early.status, early.reason, early.volume) == ("UNAVAILABLE", "GC_NO_CLOSED_MINUTE", None)
    assert (on_end.status, on_end.reason, on_end.volume) == ("AVAILABLE", None, 10.0)
    assert on_end.observed_at == at("2026-01-02T09:31:00Z")
    assert on_end.available_at == at("2026-01-02T09:31:00Z")


@pytest.mark.parametrize(
    "source, expected_reason",
    [
        (lambda: source_with(
            minute("2026-01-02T09:33:00Z"), minute("2026-01-02T09:34:00Z"),
            coverage_start=at("2026-01-02T09:32:00Z"),
        ), "GC_MINUTE_GAP"),
        (lambda: source_with(minute("2017-01-01T00:00:00Z")), "GC_DAMAGED_ERA"),
        (lambda: source_with(minute("2026-01-02T09:34:00Z", volume=math.nan)), "GC_NONFINITE_VALUE"),
        (lambda: source_with(minute("2026-01-02T09:34:00Z"), target="CME:GC"), "GC_SOURCE_IDENTITY"),
    ],
)
def test_gap_damage_nonfinite_and_identity_error_do_not_create_values(source, expected_reason):
    if expected_reason == "GC_DAMAGED_ERA":
        result = context(source(), decision_time=at("2017-01-01T00:01:00Z"), window_start=at("2017-01-01T00:00:00Z"))
    elif expected_reason == "GC_MINUTE_GAP":
        result = context(source(), decision_time=T, window_start=at("2026-01-02T09:32:00Z"))
    else:
        result = context(source(), decision_time=T, window_start=at("2026-01-02T09:34:00Z"))

    assert (result.status, result.reason, result.volume, result.delta, result.trades) == (
        "UNAVAILABLE", expected_reason, None, None, None,
    )


def test_aggregator_uses_only_closed_minutes_inside_the_callers_window():
    source = source_with(
        minute("2026-01-02T09:32:00Z", volume=4.0, delta=-1.0, trades=2.0),
        minute("2026-01-02T09:33:00Z", volume=6.0, delta=3.0, trades=4.0),
        minute("2026-01-02T09:34:00Z", volume=999.0, delta=999.0, trades=999.0, available_at="2026-01-02T09:36:00Z"),
    )

    result = context(source, decision_time=at("2026-01-02T09:34:00Z"), window_start=at("2026-01-02T09:32:00Z"))

    assert (result.status, result.volume, result.delta, result.trades) == ("AVAILABLE", 10.0, 2.0, 6.0)
    assert result.observed_at == at("2026-01-02T09:34:00Z")
    assert result.available_at == at("2026-01-02T09:34:00Z")


def test_delayed_required_minute_is_unavailable_and_context_has_no_price_surface():
    source = source_with(minute("2026-01-02T09:34:00Z", available_at="2026-01-02T09:35:01Z"))

    result = context(source, decision_time=T, window_start=at("2026-01-02T09:34:00Z"))

    assert (result.status, result.reason) == ("UNAVAILABLE", "GC_MINUTE_LATE")
    assert not {"open", "high", "low", "close", "price"} & set(result.__dataclass_fields__)


def test_no_full_minute_window_is_unavailable_and_commitment_is_deterministic():
    source = source_with(minute("2026-01-02T09:34:00Z"))
    decision = at("2026-01-02T09:34:30Z")

    first = context(source, decision_time=decision, window_start=at("2026-01-02T09:34:15Z"))
    second = context(source, decision_time=decision, window_start=at("2026-01-02T09:34:15Z"))

    assert (first.status, first.reason) == ("UNAVAILABLE", "GC_NO_CLOSED_MINUTE")
    assert first.commitment() == second.commitment()
    assert "volume" not in first.commitment()


def test_duplicate_coverage_and_overflow_are_typed_unavailable_results():
    duplicate = source_with(
        minute("2026-01-02T09:34:00Z"),
        minute("2026-01-02T09:34:00Z", volume=11.0),
    )
    assert context(duplicate, window_start=at("2026-01-02T09:34:00Z")).reason == "GC_MINUTE_DUPLICATE"

    outside = source_with(
        minute("2026-01-02T09:34:00Z"),
        coverage_end=at("2026-01-02T09:34:59Z"),
    )
    assert context(outside, window_start=at("2026-01-02T09:34:00Z")).reason == "GC_COVERAGE"

    overflowing = source_with(
        minute("2026-01-02T09:33:00Z", volume=1e308),
        minute("2026-01-02T09:34:00Z", volume=1e308),
    )
    result = context(overflowing, window_start=at("2026-01-02T09:33:00Z"))
    assert (result.status, result.reason, result.volume) == ("UNAVAILABLE", "GC_AGGREGATE_NONFINITE", None)

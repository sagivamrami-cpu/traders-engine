from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path

import pytest

from trading_system.tree_replay.cross_market_flow import (
    CrossMarketFlowContext,
    CrossMarketFlowInput,
    GcFlowMinute,
    build_cross_market_flow_context,
)
from trading_system.tree_replay.cross_market_flow_policy import CrossMarketFlowPolicy
from trading_system.tree_replay.full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    ProviderErrorPayload,
)


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
T1 = T0 + timedelta(minutes=5)
SYMBOL = "OANDA:XAUUSD"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bundle() -> FullTreeEvidenceBundle:
    artifact = FullTreeArtifact(
        artifact_id="error-1", kind="ERROR", observed_at=T0, available_at=T0,
        covered_through=T1, content_digest=digest("tree"),
        value=ProviderErrorPayload(error_type=LookupError, message="fixture"),
    )
    replay_pass = FullTreePass(
        pass_id="pass-1", decision_time=T1, source_variant="full_tree:house",
        mode="TREE_WALK", operations=(FullTreeOperation(
            operation_id="operation-1", kind="FETCH_CORRECTED",
            arguments={"symbol": SYMBOL, "timeframe": "15m", "lookback": 10},
            artifact_id="error-1", sequence=0,
        ),),
    )
    return FullTreeEvidenceBundle(
        run_id="cross-market-fixture", instrument=SYMBOL,
        artifacts=(artifact,), passes=(replay_pass,),
    )


def available_context(*, target: str = SYMBOL, decision_time: datetime = T1, volume: float = 10.0):
    policy = CrossMarketFlowPolicy.load(
        Path(__file__).resolve().parents[2] / "configs/data/xauusd-gc-crossmarket-order-flow-context.yaml",
    )
    if target != policy.target_instrument:
        policy = policy.__class__(
            target_instrument=target, source_instrument=policy.source_instrument,
            source_dataset=policy.source_dataset, archive_sha256=policy.archive_sha256,
            selected_member=policy.selected_member, allowed_columns=policy.allowed_columns,
            damaged_start=policy.damaged_start, damaged_end=policy.damaged_end,
        )
    minute = GcFlowMinute(
        minute_start=decision_time - timedelta(minutes=1), available_at=decision_time,
        volume=volume, delta=2.0, trades=3.0,
    )
    source = CrossMarketFlowInput(
        policy=policy, archive_sha256=policy.archive_sha256,
        coverage_start=minute.minute_start, coverage_end=decision_time, minutes=(minute,),
    )
    return build_cross_market_flow_context(
        source, decision_time=decision_time, window_start=minute.minute_start,
    )


def test_context_record_rejects_a_different_target_or_decision_time_than_the_parent_pass():
    from trading_system.tree_replay.full_tree_cross_market_context import FullTreeCrossMarketContextRecord

    with pytest.raises(ValueError, match="CROSS_MARKET_PARENT"):
        FullTreeCrossMarketContextRecord.capture(bundle(), "pass-1", available_context(target="CME:GC"))
    with pytest.raises(ValueError, match="CROSS_MARKET_PARENT"):
        FullTreeCrossMarketContextRecord.capture(bundle(), "pass-1", available_context(decision_time=T1 + timedelta(microseconds=1)))


def test_public_commitment_does_not_expose_raw_gc_values_and_baseline_detects_change():
    from trading_system.tree_replay.full_tree_cross_market_context import FullTreeCrossMarketContextRecord
    from trading_system.tree_replay.full_tree_checkpoint import FullTreeCrossMarketContextBaseline

    parent = bundle()
    record = FullTreeCrossMarketContextRecord.capture(parent, "pass-1", available_context())
    changed = FullTreeCrossMarketContextRecord.capture(parent, "pass-1", available_context(volume=11.0))

    public = record.commitment()
    assert "volume" not in public and "delta" not in public and "trades" not in public
    assert "10.0" not in repr(public)
    assert FullTreeCrossMarketContextBaseline.capture(parent, (record,)).baseline_digest != FullTreeCrossMarketContextBaseline.capture(parent, (changed,)).baseline_digest


def test_unavailable_context_preserves_reason_without_values_and_parent_commitment_must_match():
    from trading_system.tree_replay.full_tree_cross_market_context import FullTreeCrossMarketContextRecord
    from trading_system.tree_replay.full_tree_checkpoint import FullTreeCrossMarketContextBaseline

    unavailable = CrossMarketFlowContext(
        status="UNAVAILABLE", reason="GC_MINUTE_GAP", target_instrument=SYMBOL,
        source_instrument="CME:GC", source_dataset="DATABENTO/GLBX.MDP3",
        archive_sha256="a" * 64, decision_time=T1, window_start=T1 - timedelta(minutes=1),
        observed_at=None, available_at=None, volume=None, delta=None, trades=None,
    )
    record = FullTreeCrossMarketContextRecord.capture(bundle(), "pass-1", unavailable)
    assert record.commitment()["context"]["reason"] == "GC_MINUTE_GAP"
    assert "volume" not in record.commitment()["context"]

    with pytest.raises(ValueError, match="CROSS_MARKET_BASELINE"):
        FullTreeCrossMarketContextBaseline.capture(bundle(), (record, record))

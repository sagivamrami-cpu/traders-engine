from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.correction import Correction
from trading_system.tree_replay.full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    ProviderErrorPayload,
    TreeFramePayload,
)
from trading_system.tree_replay.full_tree_replay import FullTreeCausalReplay


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)
SYMBOL = "OANDA:XAUUSD"


def _full_frame(count=1001, freq="15min", rising=True, close=128.0, width=2.0):
    prices = [100 + index / 100 for index in range(count)] if rising else [close] * count
    return pd.DataFrame(
        {"open": [price - 0.005 for price in prices], "close": prices,
         "high": [price + width / 2 for price in prices], "low": [price - width / 2 for price in prices],
         "volume": [100.0] * count},
        index=pd.date_range(end="2026-09-09T14:00Z", periods=count, freq=freq),
    )


def _successful_full_tree_bundle(variant):
    correction = Correction(SYMBOL, 0.0, "tv_daily", "exact", "literal replay tape")
    frames = {("15m", 10): (_full_frame(), correction), ("4h", 60): (_full_frame(freq="4h"), correction)}
    for timeframe in ("1h", "30m", "15m", "5m"):
        frames[(timeframe, 30)] = (_full_frame(freq={"1h": "1h", "30m": "30min", "15m": "15min", "5m": "5min"}[timeframe]), correction)
    daily = _full_frame(220, "1D", False, close=100.0, width=20.0)
    daily.index = pd.date_range(end="2026-09-09T00:00Z", periods=220, freq="1D")
    daily["open"] = 100.0
    daily.iloc[-1, daily.columns.get_loc("high")] = 115.0
    daily.iloc[-1, daily.columns.get_loc("low")] = 95.0
    daily.iloc[-1, daily.columns.get_loc("close")] = 110.0
    frames[("1d", 400)] = (daily, correction)
    frames[("1d", 30)] = (daily, correction)
    opening = _full_frame(2, rising=False)
    opening.index = pd.to_datetime(["2026-09-09T07:00Z", "2026-09-09T13:30Z"])
    opening["open"] = [103.0, 107.0]
    frames[("5m", 3)] = (opening, correction)
    frames[("1h", 240)] = (_full_frame(1600, "1h", False, close=100.0), correction)
    frames[("4h", 240)] = (_full_frame(400, "4h", False, close=100.0), correction)

    calls = [
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "4h", "lookback": 60}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 30}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "30m", "lookback": 30}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 30}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "5m", "lookback": 30}),
        ("LIST_REPORTS", {}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1d", "lookback": 400}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 20}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 60}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "4h", "lookback": 240}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1d", "lookback": 400}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "5m", "lookback": 3}),
        ("NOW_UTC", {}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 20}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 240}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "4h", "lookback": 240}),
        *([] if variant == "house" else [("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1d", "lookback": 30})]),
        ("NOW_UTC", {}),
        ("CALENDAR_TEXT", {"path": "news-desk/data/ff_calendar.json"}),
        ("NOW_UTC", {}), ("NOW_UTC", {}), ("NOW_UTC", {}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "5m", "lookback": 5}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 5}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 30}),
        ("NOW_UTC", {}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "15m", "lookback": 10}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1d", "lookback": 400}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "5m", "lookback": 3}),
        ("NOW_UTC", {}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 20}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1h", "lookback": 240}),
        ("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "4h", "lookback": 240}),
        *([] if variant == "house" else [("FETCH_CORRECTED", {"symbol": SYMBOL, "timeframe": "1d", "lookback": 30})]),
    ]
    decision = datetime(2026, 9, 9, 14, 0, tzinfo=timezone.utc)
    artifacts, operations = [], []
    for sequence, (kind, arguments) in enumerate(calls):
        artifact_id = f"artifact-{sequence}"
        if kind == "FETCH_CORRECTED":
            frame_key = (arguments["timeframe"], arguments["lookback"])
            if frame_key in frames:
                value = TreeFramePayload(frame=frames[frame_key][0], correction=correction)
                artifact_kind = "FRAME"
            else:
                value = ProviderErrorPayload(error_type=LookupError, message="raw tape unavailable")
                artifact_kind = "ERROR"
        elif kind == "LIST_REPORTS":
            value, artifact_kind = [], "REPORT_LIST"
        elif kind == "NOW_UTC":
            value, artifact_kind = pd.Timestamp(decision), "CLOCK"
        else:
            value = json.dumps([{"dateline": decision.timestamp() + 86400, "impact": "Low", "title": "future"}])
            artifact_kind = "TEXT"
        artifacts.append(FullTreeArtifact(
            artifact_id=artifact_id, kind=artifact_kind, observed_at=decision,
            available_at=decision, covered_through=decision, content_digest=f"{sequence:064x}", value=value,
        ))
        operations.append(FullTreeOperation(
            operation_id=f"operation-{sequence}", kind=kind, arguments=arguments,
            artifact_id=artifact_id, sequence=sequence,
        ))
    return FullTreeEvidenceBundle(
        run_id=f"full-tree-{variant}", instrument=SYMBOL, artifacts=tuple(artifacts),
        passes=(FullTreePass(
            pass_id=f"{variant}-pass", decision_time=decision, source_variant=f"full_tree:{variant}",
            mode="TREE_WALK", operations=tuple(operations),
        ),),
    )


def test_actual_tree_reader_turns_a_scheduled_data_error_into_a_tree_stop():
    bundle = FullTreeEvidenceBundle(
        run_id="full-tree-run-1",
        instrument=SYMBOL,
        artifacts=(FullTreeArtifact(
            artifact_id="initial-frame-error",
            kind="ERROR",
            observed_at=T0,
            available_at=T0,
            covered_through=T1,
            content_digest="a" * 64,
            value=ProviderErrorPayload(error_type=LookupError, message="tape unavailable"),
        ),),
        passes=(FullTreePass(
            pass_id="pass-1",
            decision_time=T1,
            source_variant="full_tree:house",
            mode="TREE_WALK",
            operations=(FullTreeOperation(
                operation_id="first-data-fetch",
                kind="FETCH_CORRECTED",
                arguments={"symbol": SYMBOL, "timeframe": "15m", "lookback": 10},
                artifact_id="initial-frame-error",
                sequence=0,
            ),),
        ),),
    )

    result = FullTreeCausalReplay(bundle).run_pass("pass-1")

    assert result.record.outcome == "TREE_STOPPED"
    assert result.record.reached_stage == "DATA"
    assert result.record.direction is None
    assert result.record.plan_digest is None
    assert result.record.trace_digest != ""


@pytest.mark.parametrize("variant", ("house", "strict"))
def test_actual_complete_tree_observes_a_candidate_from_literal_scheduled_evidence(variant):
    evidence = _successful_full_tree_bundle(variant)

    result = FullTreeCausalReplay(evidence).run_pass(f"{variant}-pass")

    assert result.record.source_variant == f"full_tree:{variant}"
    assert result.record.outcome == "TREE_CANDIDATE_OBSERVED"
    assert result.record.reached_stage == "TARGET"
    assert result.record.direction == "לונג"
    assert result.record.plan_digest is not None
    assert result.record.unreached_operation_ids == ()


def test_runner_requires_pass_order_and_hash_chains_actual_source_observations():
    def source_error(artifact_id, digest):
        return FullTreeArtifact(
            artifact_id=artifact_id,
            kind="ERROR",
            observed_at=T0,
            available_at=T0,
            covered_through=T1 + timedelta(minutes=5),
            content_digest=digest,
            value=ProviderErrorPayload(error_type=LookupError, message="tape unavailable"),
        )

    def pass_at(pass_id, at, artifact_id):
        return FullTreePass(
            pass_id=pass_id,
            decision_time=at,
            source_variant="full_tree:house",
            mode="TREE_WALK",
            operations=(FullTreeOperation(
                operation_id=f"{pass_id}-fetch",
                kind="FETCH_CORRECTED",
                arguments={"symbol": SYMBOL, "timeframe": "15m", "lookback": 10},
                artifact_id=artifact_id,
                sequence=0,
            ),),
        )

    replay = FullTreeCausalReplay(FullTreeEvidenceBundle(
        run_id="full-tree-run-ordered",
        instrument=SYMBOL,
        artifacts=(source_error("error-1", "a" * 64), source_error("error-2", "b" * 64)),
        passes=(pass_at("pass-1", T1, "error-1"), pass_at("pass-2", T1 + timedelta(minutes=5), "error-2")),
    ))

    with pytest.raises(ValueError, match="FULL_TREE_PASS_ORDER"):
        replay.run_pass("pass-2")

    first = replay.run_pass("pass-1").record
    second = replay.run_pass("pass-2").record

    assert second.previous_record_digest == first.record_digest
    with pytest.raises(ValueError, match="FULL_TREE_PASS_ORDER"):
        replay.run_pass("pass-2")

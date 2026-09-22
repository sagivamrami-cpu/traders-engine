from dataclasses import replace
from datetime import UTC, datetime

import pytest

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.gc_normalized_feature_model import (
    materialize_normalized_features,
    train_gc_normalized_feature_model,
)
from trading_system.models.readiness import TrainingPolicy

FIXED_TIME = datetime(2026, 9, 7, 18, 0, tzinfo=UTC)


def row(
    row_id: str,
    outcome_class: str,
    split: str,
    *,
    ret_1: float,
    of_delta: float,
    close: float = 1000.0,
    atr_14: float = 4.0,
    of_volume: float = 100.0,
    of_trades: float = 5.0,
    of_minutes_present: float = 30.0,
    included: bool = True,
) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=row_id,
        dataset_id="fixture-gc-dataset",
        dataset_version="gc-30m-real-dataset-builder-0.1.0",
        snapshot_id=f"snapshot-{row_id}",
        candidate_id=f"candidate-{row_id}",
        symbol="GC",
        observation_time=datetime(2026, 8, 28, 13, 30, tzinfo=UTC),
        graph_id="gc-30m-outcome-contract",
        graph_version="gc-30m-real-dataset-builder-0.1.0",
        direction="LONG" if ret_1 >= 0 else "SHORT",
        candidate_status="ELIGIBLE" if included else "REJECTED",
        features={
            "close": close,
            "atr_14": atr_14,
            "ret_1": ret_1,
            "ret_4": ret_1 * 2,
            "ret_8": ret_1 * 3,
            "ret_14": ret_1 * 4,
            "range_over_atr": abs(ret_1) + 1.0,
            "volume_30m": of_volume,
            "seconds_with_trades": 120.0,
            "of_volume": of_volume,
            "of_delta": of_delta,
            "of_trades": of_trades,
            "of_minutes_present": of_minutes_present,
            "of_volume_sum_14": of_volume * 14,
            "of_delta_sum_14": of_delta * 14,
            "of_trades_sum_14": of_trades * 14,
        },
        feature_schema_version="gc-30m-real-feature-schema-0.1.0",
        contract_version="gc-atr14-1r-1r-8bar-zero-cost-0.1.0",
        label_version="gc-outcome-contract-label-0.1.0",
        outcome_class=outcome_class if included else None,
        label_quality="HIGH" if included else "EXCLUDED_FROM_TRAINING",
        included_in_training=included,
        exclusion_reasons=() if included else ("AMBIGUOUS_LABEL",),
        split=split,
        source_hashes={"ohlcv_1s_zip": "a" * 64, "order_flow_zip": "b" * 64},
        outcome_return_r=1.0 if outcome_class == "TARGET_FIRST" else -1.0,
    )


def policy() -> TrainingPolicy:
    return TrainingPolicy(
        version="baseline-training-policy-0.1.0",
        min_train_rows=4,
        min_validation_rows=2,
        min_classes=2,
    )


def feature_candidates() -> dict:
    return {
        "report_id": "c" * 64,
        "report_version": "gc-normalized-feature-candidates-report-0.1.0",
        "status": "NORMALIZED_FEATURE_CANDIDATES_READY",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "research_training_allowed": True,
        "model_promotion_allowed": False,
        "next_model_feature_set": [
            "ret_1",
            "ret_4",
            "ret_8",
            "ret_14",
            "range_over_atr",
            "direction_is_long",
            "direction_is_short",
            "atr_14_over_close",
            "of_delta_over_of_volume",
            "of_delta_sum_14_over_of_volume_sum_14",
            "of_trades_per_minute",
            "of_volume_per_trade",
            "of_volume_vs_14bar_avg",
            "of_trades_vs_14bar_avg",
        ],
        "excluded_raw_features": [
            {"feature": "close", "reason": "RAW_PRICE_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
            {"feature": "atr_14", "reason": "RAW_ATR_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
        ],
        "forbidden_feature_inputs": [
            "outcome_class",
            "net_return_r",
            "time_to_outcome_bars",
            "entry_price",
            "target_price",
            "stop_price",
            "risk_r",
        ],
        "required_training_controls": [
            "TRAIN_ONLY_IMPUTATION_AND_STANDARDIZATION",
            "VALIDATION_ONLY_THRESHOLD_SELECTION",
            "TEST_ONLY_FINAL_EVALUATION",
            "NO_LABEL_OR_OUTCOME_FEATURE_INPUTS",
        ],
    }


def previous_model_run() -> dict:
    return {
        "run_id": "d" * 64,
        "metrics": {
            "validation_accuracy": 0.42,
            "test_accuracy": 0.44,
            "validation_expected_r_per_candidate": 0.002,
            "test_expected_r_per_candidate": -0.001,
        },
    }


def baseline_run() -> dict:
    return {
        "run_id": "e" * 64,
        "metrics": {
            "validation_accuracy": 0.41,
            "test_accuracy": 0.43,
        },
    }


def fixture_candidate_rows() -> list[CandidateTrainingRow]:
    return [
        row("1", "TARGET_FIRST", "TRAIN", ret_1=0.05, of_delta=9.0),
        row("2", "TARGET_FIRST", "TRAIN", ret_1=0.04, of_delta=8.0),
        row("3", "STOP_FIRST", "TRAIN", ret_1=-0.05, of_delta=-9.0),
        row("4", "STOP_FIRST", "TRAIN", ret_1=-0.04, of_delta=-8.0),
        row("5", "TARGET_FIRST", "VALIDATION", ret_1=0.045, of_delta=8.5),
        row("6", "STOP_FIRST", "VALIDATION", ret_1=-0.045, of_delta=-8.5),
        row("7", "TARGET_FIRST", "TEST", ret_1=0.046, of_delta=8.6),
        row("8", "STOP_FIRST", "TEST", ret_1=-0.046, of_delta=-8.6),
        row("9", "STOP_FIRST", "TRAIN", ret_1=0.50, of_delta=99.0, included=False),
    ]


def test_materialize_normalized_features_computes_zero_safe_ratios():
    features = materialize_normalized_features(
        row("1", "TARGET_FIRST", "TRAIN", ret_1=0.05, of_delta=10.0, close=2000.0, atr_14=8.0),
        feature_candidates(),
    )

    assert features["atr_14_over_close"] == 0.004
    assert features["of_delta_over_of_volume"] == 0.1
    assert features["of_delta_sum_14_over_of_volume_sum_14"] == 0.1
    assert features["of_trades_per_minute"] == pytest.approx(1 / 6)
    assert features["of_volume_per_trade"] == 20.0
    assert features["of_volume_vs_14bar_avg"] == 1.0
    assert features["of_trades_vs_14bar_avg"] == 1.0

    zero_volume = materialize_normalized_features(
        row("2", "STOP_FIRST", "TRAIN", ret_1=-0.05, of_delta=-10.0, of_volume=0.0, of_trades=0.0),
        feature_candidates(),
    )
    assert zero_volume["of_delta_over_of_volume"] is None
    assert zero_volume["of_volume_per_trade"] is None


def test_normalized_feature_model_trains_without_raw_drifted_inputs():
    payload = train_gc_normalized_feature_model(
        fixture_candidate_rows(),
        policy(),
        feature_candidates(),
        previous_model_run(),
        baseline_run(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert payload["status"] == "TRAINED"
    assert payload["model_type"] == "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH"
    assert payload["promotion_allowed"] is False
    assert payload["source_feature_candidates_report_id"] == "c" * 64
    assert "close" not in payload["feature_names"]
    assert "atr_14" not in payload["feature_names"]
    assert "atr_14_over_close" in payload["feature_names"]
    assert "of_delta_over_of_volume" in payload["feature_names"]
    assert payload["comparison_metrics"]["previous_model_run_id"] == "d" * 64
    assert "test_accuracy_delta_vs_previous_model" in payload["comparison_metrics"]


def test_normalized_feature_model_blocks_unapproved_candidate_report():
    candidates = {**feature_candidates(), "research_training_allowed": False}

    payload = train_gc_normalized_feature_model(
        fixture_candidate_rows(),
        policy(),
        candidates,
        previous_model_run(),
        baseline_run(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "FEATURE_CANDIDATES_NOT_RESEARCH_TRAINABLE" in payload["blocked_reasons"]


def test_normalized_feature_model_schema_rejects_promotion_allowed():
    run = train_gc_normalized_feature_model(
        fixture_candidate_rows(),
        policy(),
        feature_candidates(),
        previous_model_run(),
        baseline_run(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()


def test_normalized_feature_model_blocks_forbidden_candidate_feature_names():
    candidates = {
        **feature_candidates(),
        "next_model_feature_set": [*feature_candidates()["next_model_feature_set"], "net_return_r"],
    }

    payload = train_gc_normalized_feature_model(
        [replace(fixture_candidate_rows()[0], split="TRAIN"), *fixture_candidate_rows()[1:]],
        policy(),
        candidates,
        previous_model_run(),
        baseline_run(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "FORBIDDEN_FEATURE_PRESENT:net_return_r" in payload["blocked_reasons"]

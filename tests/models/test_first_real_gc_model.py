from dataclasses import replace
from datetime import UTC, datetime

import pytest

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.first_real_gc_model import train_first_real_gc_model
from trading_system.models.readiness import TrainingPolicy

FIXED_TIME = datetime(2026, 9, 7, 14, 0, tzinfo=UTC)


def row(
    row_id: str,
    outcome_class: str,
    split: str,
    *,
    ret_1: float,
    of_delta: float,
    outcome_return_r: float | None = None,
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
            "close": 1000.0 + ret_1,
            "atr_14": 4.0,
            "ret_1": ret_1,
            "ret_4": ret_1 * 2,
            "ret_8": ret_1 * 3,
            "ret_14": ret_1 * 4,
            "range_over_atr": abs(ret_1) + 1.0,
            "volume_30m": 100.0,
            "seconds_with_trades": 120.0,
            "of_volume": 100.0,
            "of_delta": of_delta,
            "of_trades": 3.0,
            "of_minutes_present": 30.0,
            "of_volume_sum_14": 1400.0,
            "of_delta_sum_14": of_delta * 14,
            "of_trades_sum_14": 42.0,
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
        outcome_return_r=outcome_return_r,
    )


def policy() -> TrainingPolicy:
    return TrainingPolicy(
        version="baseline-training-policy-0.1.0",
        min_train_rows=4,
        min_validation_rows=2,
        min_classes=2,
    )


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


def test_first_real_model_fits_only_train_and_reports_validation_and_test_metrics():
    run = train_first_real_gc_model(fixture_candidate_rows(), policy(), created_at=FIXED_TIME)
    payload = run.to_payload()

    assert payload["status"] == "TRAINED"
    assert payload["model_type"] == "REGULARIZED_LOGISTIC_RESEARCH_BASELINE"
    assert payload["promotion_allowed"] is False
    assert payload["fit_scope"] == "TRAIN_ONLY"
    assert payload["selection_scope"] == "VALIDATION_ONLY"
    assert payload["final_evaluation_scope"] == "TEST_ONLY"
    assert payload["threshold_selection_metric"] == "validation_expected_r_per_candidate"
    assert payload["selected_threshold"] > 0
    assert set(payload["feature_names"]) >= {"ret_1", "of_delta", "direction_is_long"}
    assert set(payload["metrics"]) >= {
        "validation_accuracy",
        "test_accuracy",
        "validation_balanced_accuracy",
        "test_balanced_accuracy",
        "validation_expected_r_per_candidate",
        "test_expected_r_per_candidate",
    }


def test_first_real_model_returns_blocked_run_when_training_readiness_fails():
    run = train_first_real_gc_model(
        [row("1", "TARGET_FIRST", "TRAIN", ret_1=0.05, of_delta=9.0)],
        policy(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()

    assert payload["status"] == "BLOCKED"
    assert payload["model_version"] is None
    assert payload["promotion_allowed"] is False
    assert "INSUFFICIENT_TRAIN_ROWS" in payload["blocked_reasons"]


def test_first_real_model_schema_rejects_promotion_allowed():
    run = train_first_real_gc_model(fixture_candidate_rows(), policy(), created_at=FIXED_TIME)
    payload = run.to_payload()
    payload["promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()


def test_first_real_model_expected_r_uses_dataset_net_return_r():
    rows = [
        row("1", "TARGET_FIRST", "TRAIN", ret_1=0.05, of_delta=9.0, outcome_return_r=1.0),
        row("2", "TARGET_FIRST", "TRAIN", ret_1=0.04, of_delta=8.0, outcome_return_r=1.0),
        row("3", "STOP_FIRST", "TRAIN", ret_1=-0.05, of_delta=-9.0, outcome_return_r=-1.0),
        row("4", "STOP_FIRST", "TRAIN", ret_1=-0.04, of_delta=-8.0, outcome_return_r=-1.0),
        row("5", "TARGET_FIRST", "VALIDATION", ret_1=0.045, of_delta=8.5, outcome_return_r=0.25),
        row("6", "STOP_FIRST", "VALIDATION", ret_1=-0.045, of_delta=-8.5, outcome_return_r=-1.0),
        row("7", "TARGET_FIRST", "TEST", ret_1=0.046, of_delta=8.6, outcome_return_r=0.5),
        row("8", "STOP_FIRST", "TEST", ret_1=-0.046, of_delta=-8.6, outcome_return_r=-1.0),
    ]

    payload = train_first_real_gc_model(rows, policy(), created_at=FIXED_TIME).to_payload()

    assert payload["metrics"]["validation_expected_r_per_selected_trade"] == 0.25
    assert payload["metrics"]["test_expected_r_per_selected_trade"] == 0.5


def test_first_real_model_blocks_leaky_feature_names():
    rows = fixture_candidate_rows()
    rows[0] = replace(rows[0], features={**rows[0].features, "net_return_r": 1.0})

    payload = train_first_real_gc_model(rows, policy(), created_at=FIXED_TIME).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "FORBIDDEN_FEATURE_PRESENT:net_return_r" in payload["blocked_reasons"]

from datetime import UTC, datetime, timedelta

import pytest

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.gc_normalized_model_stability import build_gc_normalized_model_stability_report

FIXED_TIME = datetime(2026, 9, 7, 19, 0, tzinfo=UTC)


def row(
    row_id: str,
    outcome_class: str,
    split: str,
    *,
    index: int,
    direction: str,
    ret_1: float,
    of_delta: float,
    close: float,
    atr_14: float,
) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=row_id,
        dataset_id="fixture-gc-dataset",
        dataset_version="gc-30m-real-dataset-builder-0.1.0",
        snapshot_id=f"snapshot-{row_id}",
        candidate_id=f"candidate-{row_id}",
        symbol="GC",
        observation_time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index * 35),
        graph_id="gc-30m-outcome-contract",
        graph_version="gc-30m-real-dataset-builder-0.1.0",
        direction=direction,
        candidate_status="ELIGIBLE",
        features={
            "close": close,
            "atr_14": atr_14,
            "ret_1": ret_1,
            "ret_4": ret_1 * 2,
            "ret_8": ret_1 * 3,
            "ret_14": ret_1 * 4,
            "range_over_atr": abs(ret_1) + 1.0,
            "of_volume": 100.0,
            "of_delta": of_delta,
            "of_trades": 5.0,
            "of_minutes_present": 30.0,
            "of_volume_sum_14": 1400.0,
            "of_delta_sum_14": of_delta * 14,
            "of_trades_sum_14": 70.0,
        },
        feature_schema_version="gc-30m-real-feature-schema-0.1.0",
        contract_version="gc-atr14-1r-1r-8bar-zero-cost-0.1.0",
        label_version="gc-outcome-contract-label-0.1.0",
        outcome_class=outcome_class,
        label_quality="HIGH",
        included_in_training=True,
        exclusion_reasons=(),
        split=split,
        source_hashes={"ohlcv_1s_zip": "a" * 64, "order_flow_zip": "b" * 64},
        outcome_return_r=1.0 if outcome_class == "TARGET_FIRST" else -1.0,
    )


def rows() -> list[CandidateTrainingRow]:
    return [
        row("1", "TARGET_FIRST", "TRAIN", index=0, direction="LONG", ret_1=0.05, of_delta=8.0, close=1000, atr_14=2),
        row("2", "STOP_FIRST", "TRAIN", index=1, direction="SHORT", ret_1=-0.05, of_delta=-8.0, close=1000, atr_14=5),
        row("3", "TARGET_FIRST", "TRAIN", index=2, direction="LONG", ret_1=0.04, of_delta=7.0, close=1000, atr_14=8),
        row("4", "STOP_FIRST", "TRAIN", index=3, direction="SHORT", ret_1=-0.04, of_delta=-7.0, close=1000, atr_14=3),
        row("5", "TARGET_FIRST", "TEST", index=4, direction="LONG", ret_1=0.03, of_delta=6.0, close=1100, atr_14=2),
        row("6", "STOP_FIRST", "TEST", index=5, direction="SHORT", ret_1=-0.03, of_delta=-6.0, close=1100, atr_14=6),
        row("7", "TARGET_FIRST", "TEST", index=6, direction="LONG", ret_1=0.02, of_delta=4.0, close=1200, atr_14=9),
    ]


def feature_candidates() -> dict:
    return {
        "report_id": "c" * 64,
        "report_version": "gc-normalized-feature-candidates-report-0.1.0",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
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
    }


def model_run() -> dict:
    return {
        "run_id": "d" * 64,
        "run_version": "gc-normalized-feature-model-run-0.1.0",
        "dataset_id": "fixture-gc-dataset",
        "model_type": "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH",
        "model_version": "normalized-feature-logistic-research-0.1.0",
        "selected_threshold": 0.5,
        "feature_names": feature_candidates()["next_model_feature_set"],
        "intercept": 0.0,
        "coefficients": {
            "ret_1": 1.0,
            "ret_4": 0.5,
            "ret_8": 0.25,
            "ret_14": 0.1,
            "range_over_atr": 0.0,
            "direction_is_long": 0.2,
            "direction_is_short": -0.2,
            "atr_14_over_close": 0.0,
            "of_delta_over_of_volume": 0.5,
            "of_delta_sum_14_over_of_volume_sum_14": 0.1,
            "of_trades_per_minute": 0.0,
            "of_volume_per_trade": 0.0,
            "of_volume_vs_14bar_avg": 0.0,
            "of_trades_vs_14bar_avg": 0.0,
        },
        "promotion_allowed": False,
    }


def test_stability_report_scores_test_segments_and_keeps_promotion_blocked():
    report = build_gc_normalized_model_stability_report(
        rows(),
        feature_candidates(),
        model_run(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert report["status"] == "STABILITY_REVIEW_REQUIRED"
    assert report["promotion_allowed"] is False
    assert report["evaluation_scope"] == "TEST_ONLY"
    assert report["preprocessing_reconstruction_scope"] == "TRAIN_ONLY"
    assert report["source_model_run_id"] == "d" * 64
    assert report["monthly_test_segments"]
    assert set(report["direction_test_segments"]) == {"LONG", "SHORT"}
    assert set(report["volatility_test_segments"]) == {"LOW", "MID", "HIGH"}
    assert len(report["threshold_stability"]) == 3
    assert "MODEL_PROMOTION" in report["blocked_actions"]


def test_stability_schema_rejects_promotion_allowed():
    run = build_gc_normalized_model_stability_report(
        rows(),
        feature_candidates(),
        model_run(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

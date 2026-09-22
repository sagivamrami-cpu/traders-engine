from datetime import UTC, datetime

import pytest

from trading_system.models.gc_model_diagnostics import build_gc_model_diagnostics_report

FIXED_TIME = datetime(2026, 9, 7, 15, 0, tzinfo=UTC)

BASELINE_RUN = {
    "run_id": "a" * 64,
    "run_version": "model-training-run-0.1.0",
    "status": "TRAINED",
    "dataset_id": "fixture-gc-dataset",
    "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
    "model_type": "MAJORITY_CLASS_BASELINE",
    "model_version": "majority-class-baseline-0.1.0",
    "created_at": "2026-09-07T13:22:35Z",
    "training_policy_version": "baseline-training-policy-0.1.0",
    "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
    "label_version": "gc-outcome-contract-label-0.1.0",
    "split_summary": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
    "class_distribution": {"STOP_FIRST": 4, "TARGET_FIRST": 4},
    "baseline_class": "STOP_FIRST",
    "metrics": {"validation_accuracy": 0.42, "test_accuracy": 0.44},
    "blocked_reasons": [],
    "promotion_allowed": False,
}

FIRST_MODEL_RUN = {
    "run_id": "b" * 64,
    "run_version": "gc-first-real-model-run-0.1.0",
    "status": "TRAINED",
    "dataset_id": "fixture-gc-dataset",
    "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
    "model_type": "REGULARIZED_LOGISTIC_RESEARCH_BASELINE",
    "model_version": "regularized-logistic-research-baseline-0.1.0",
    "created_at": "2026-09-07T14:01:41Z",
    "training_policy_version": "baseline-training-policy-0.1.0",
    "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
    "label_version": "gc-outcome-contract-label-0.1.0",
    "split_summary": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
    "class_distribution": {"STOP_FIRST": 4, "TARGET_FIRST": 4},
    "fit_scope": "TRAIN_ONLY",
    "selection_scope": "VALIDATION_ONLY",
    "final_evaluation_scope": "TEST_ONLY",
    "feature_names": ["ret_1", "of_delta", "direction_is_long"],
    "training_parameters": {"solver": "in_repo_batch_gradient_descent"},
    "selected_threshold": 0.56,
    "threshold_selection_metric": "validation_expected_r_per_candidate",
    "intercept": -0.01,
    "coefficients": {"ret_1": 0.2, "of_delta": -0.5, "direction_is_long": 0.1},
    "metrics": {
        "validation_accuracy": 0.43,
        "test_accuracy": 0.439,
        "validation_expected_r_per_candidate": 0.002,
        "test_expected_r_per_candidate": -0.001,
        "validation_selected_trade_rate": 0.19,
        "test_selected_trade_rate": 0.13,
    },
    "blocked_reasons": [],
    "promotion_allowed": False,
}


def test_diagnostics_blocks_promotion_when_test_expected_r_is_negative():
    report = build_gc_model_diagnostics_report(BASELINE_RUN, FIRST_MODEL_RUN, created_at=FIXED_TIME).to_payload()

    assert report["status"] == "FEATURE_DIAGNOSTICS_REQUIRED"
    assert report["promotion_allowed"] is False
    assert "NEGATIVE_TEST_EXPECTED_R" in report["blocked_reasons"]
    assert "TEST_ACCURACY_NOT_ABOVE_BASELINE" in report["blocked_reasons"]
    assert report["metric_deltas"]["test_accuracy_delta_vs_baseline"] == pytest.approx(-0.001)
    assert report["metric_deltas"]["validation_accuracy_delta_vs_baseline"] == pytest.approx(0.01)
    assert report["top_coefficients"][0] == {"feature": "of_delta", "coefficient": -0.5, "abs_coefficient": 0.5}
    assert report["recommended_next_phase"] == "PHASE_50_FEATURE_DIAGNOSTICS_AND_EXPERIMENT_DESIGN"


def test_diagnostics_schema_rejects_promotion_allowed():
    payload = build_gc_model_diagnostics_report(BASELINE_RUN, FIRST_MODEL_RUN, created_at=FIXED_TIME).to_payload()
    payload["promotion_allowed"] = True

    with pytest.raises(Exception):
        build_gc_model_diagnostics_report(BASELINE_RUN, FIRST_MODEL_RUN, created_at=FIXED_TIME).__class__(payload).to_payload()

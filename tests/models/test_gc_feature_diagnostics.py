from datetime import UTC, datetime

import pandas as pd
import pytest

from trading_system.models.gc_feature_diagnostics import build_gc_feature_diagnostics_report

FIXED_TIME = datetime(2026, 9, 7, 16, 0, tzinfo=UTC)


def rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "split": "TRAIN",
                "included_order_flow": True,
                "outcome_class": "TARGET_FIRST",
                "direction": "LONG",
                "net_return_r": 1.0,
                "of_delta": 10.0,
                "ret_14": 0.05,
                "atr_14": 2.0,
            },
            {
                "split": "TRAIN",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "SHORT",
                "net_return_r": -1.0,
                "of_delta": -10.0,
                "ret_14": -0.05,
                "atr_14": 6.0,
            },
            {
                "split": "VALIDATION",
                "included_order_flow": True,
                "outcome_class": "TARGET_FIRST",
                "direction": "LONG",
                "net_return_r": 1.0,
                "of_delta": 12.0,
                "ret_14": 0.04,
                "atr_14": 3.0,
            },
            {
                "split": "VALIDATION",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "SHORT",
                "net_return_r": -1.0,
                "of_delta": -12.0,
                "ret_14": -0.04,
                "atr_14": 7.0,
            },
            {
                "split": "TEST",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "LONG",
                "net_return_r": -1.0,
                "of_delta": 100.0,
                "ret_14": 0.03,
                "atr_14": 8.0,
            },
            {
                "split": "TEST",
                "included_order_flow": True,
                "outcome_class": "EXPIRED",
                "direction": "SHORT",
                "net_return_r": -0.2,
                "of_delta": 80.0,
                "ret_14": -0.03,
                "atr_14": 9.0,
            },
            {
                "split": "TEST",
                "included_order_flow": False,
                "outcome_class": "TARGET_FIRST",
                "direction": "LONG",
                "net_return_r": 1.0,
                "of_delta": 500.0,
                "ret_14": 0.10,
                "atr_14": 10.0,
            },
        ]
    )


def build_manifest() -> dict:
    return {
        "dataset_id": "fixture-gc-dataset",
        "builder_version": "gc-30m-real-dataset-builder-0.1.0",
        "summary": {
            "variants": {
                "order_flow": {
                    "included_rows_by_split": {"TRAIN": 2, "VALIDATION": 2, "TEST": 2},
                    "included_rows": 6,
                }
            }
        },
    }


def first_model_run() -> dict:
    return {
        "run_id": "a" * 64,
        "dataset_id": "fixture-gc-dataset",
        "model_type": "REGULARIZED_LOGISTIC_RESEARCH_BASELINE",
        "feature_names": ["of_delta", "ret_14", "atr_14", "direction_is_long", "direction_is_short"],
        "metrics": {
            "validation_expected_r_per_candidate": 0.002,
            "test_expected_r_per_candidate": -0.001,
        },
        "promotion_allowed": False,
    }


def model_diagnostics() -> dict:
    return {
        "report_id": "b" * 64,
        "status": "FEATURE_DIAGNOSTICS_REQUIRED",
        "blocked_reasons": ["NEGATIVE_TEST_EXPECTED_R", "TEST_ACCURACY_NOT_ABOVE_BASELINE"],
        "promotion_allowed": False,
    }


def test_feature_diagnostics_reports_drift_regimes_and_blocks_promotion():
    report = build_gc_feature_diagnostics_report(
        rows(),
        build_manifest(),
        first_model_run(),
        model_diagnostics(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert report["status"] == "EXPERIMENT_DESIGN_REQUIRED"
    assert report["promotion_allowed"] is False
    assert report["diagnostic_focus"] == "FEATURE_AND_REGIME_STABILITY"
    assert report["dataset_id"] == "fixture-gc-dataset"
    assert report["variant"] == "order_flow"
    assert report["included_rows_by_split"] == {"TRAIN": 2, "VALIDATION": 2, "TEST": 2}
    assert report["top_drift_features"][0]["feature"] == "of_delta"
    assert report["feature_summaries"]["of_delta"]["train_target_mean"] == 10.0
    assert report["feature_summaries"]["of_delta"]["train_non_target_mean"] == -10.0
    assert report["regime_summaries"]["direction=LONG"]["TEST"]["mean_return_r"] == -1.0
    assert "ORDER_FLOW_FEATURE_STABILITY_REVIEW" in report["recommended_experiments"]
    assert "REGIME_FILTER_RESEARCH" in report["recommended_experiments"]


def test_feature_diagnostics_schema_rejects_promotion_allowed():
    run = build_gc_feature_diagnostics_report(
        rows(),
        build_manifest(),
        first_model_run(),
        model_diagnostics(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

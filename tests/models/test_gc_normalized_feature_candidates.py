from datetime import UTC, datetime

import pytest

from trading_system.models.gc_normalized_feature_candidates import build_gc_normalized_feature_candidates_report

FIXED_TIME = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)


def feature_diagnostics() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-feature-diagnostics-report-0.1.0",
        "mode": "GC_FEATURE_DIAGNOSTICS",
        "created_at": "2026-09-07T16:00:00Z",
        "status": "EXPERIMENT_DESIGN_REQUIRED",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "diagnostic_focus": "FEATURE_AND_REGIME_STABILITY",
        "source_model_run_id": "b" * 64,
        "source_model_diagnostics_report_id": "c" * 64,
        "included_rows_by_split": {"TRAIN": 10, "VALIDATION": 5, "TEST": 5},
        "feature_summaries": {
            "close": {"test_drift_z": 8.0},
            "atr_14": {"test_drift_z": 3.5},
            "of_delta": {"test_drift_z": 0.1},
        },
        "top_drift_features": [
            {"feature": "close", "test_drift_z": 8.0, "validation_drift_z": 1.8},
            {"feature": "atr_14", "test_drift_z": 3.5, "validation_drift_z": 0.3},
            {"feature": "of_trades", "test_drift_z": 0.2, "validation_drift_z": 0.1},
        ],
        "regime_summaries": {},
        "recommended_experiments": [
            "FAILED_TRADE_CLUSTER_REVIEW",
            "ORDER_FLOW_FEATURE_STABILITY_REVIEW",
            "REGIME_FILTER_RESEARCH",
            "THRESHOLD_STABILITY_REVIEW",
        ],
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
        "promotion_allowed": False,
    }


def test_normalized_feature_candidates_exclude_raw_drifted_features_and_allow_research_training():
    report = build_gc_normalized_feature_candidates_report(feature_diagnostics(), created_at=FIXED_TIME).to_payload()

    assert report["status"] == "NORMALIZED_FEATURE_CANDIDATES_READY"
    assert report["research_training_allowed"] is True
    assert report["model_promotion_allowed"] is False
    assert report["dataset_id"] == "fixture-gc-dataset"
    assert report["variant"] == "order_flow"
    assert report["recommended_next_phase"] == "PHASE_52_NORMALIZED_FEATURE_MODEL_RETRAINING"
    assert "close" not in report["next_model_feature_set"]
    assert "atr_14" not in report["next_model_feature_set"]
    assert "atr_14_over_close" in report["next_model_feature_set"]
    assert "of_delta_over_of_volume" in report["next_model_feature_set"]
    assert report["excluded_raw_features"] == [
        {"feature": "close", "reason": "RAW_PRICE_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
        {"feature": "atr_14", "reason": "RAW_ATR_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
    ]


def test_normalized_feature_candidates_define_zero_safe_order_flow_ratios_and_leakage_guard():
    report = build_gc_normalized_feature_candidates_report(feature_diagnostics(), created_at=FIXED_TIME).to_payload()
    definitions = {item["name"]: item for item in report["normalized_feature_definitions"]}

    assert definitions["of_delta_over_of_volume"]["formula"] == "of_delta / of_volume"
    assert definitions["of_delta_over_of_volume"]["zero_denominator_policy"] == "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE"
    assert definitions["of_volume_per_trade"]["zero_denominator_policy"] == "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE"
    assert "ORDER_FLOW_NORMALIZED" in report["feature_groups"]
    assert "of_delta_over_of_volume" in report["feature_groups"]["ORDER_FLOW_NORMALIZED"]
    for forbidden in report["forbidden_feature_inputs"]:
        assert forbidden not in report["next_model_feature_set"]


def test_normalized_feature_candidates_schema_rejects_model_promotion_allowed():
    run = build_gc_normalized_feature_candidates_report(feature_diagnostics(), created_at=FIXED_TIME)
    payload = run.to_payload()
    payload["model_promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

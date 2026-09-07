from datetime import UTC, datetime

import pytest

from trading_system.models.gc_walk_forward_experiments import build_gc_walk_forward_experiments_report

FIXED_TIME = datetime(2026, 9, 7, 20, 0, tzinfo=UTC)


def segment(rows: int, expected_r: float | None, selected_r: float | None = None) -> dict:
    return {
        "rows": rows,
        "accuracy": 0.44 if expected_r is not None else None,
        "target_precision": 0.51 if expected_r is not None else None,
        "target_recall": 0.36 if expected_r is not None else None,
        "selected_trade_rate": 0.32 if expected_r is not None else None,
        "expected_r_per_candidate": expected_r,
        "expected_r_per_selected_trade": selected_r if selected_r is not None else expected_r,
    }


def stability_report() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-normalized-model-stability-report-0.1.0",
        "mode": "GC_NORMALIZED_MODEL_STABILITY",
        "created_at": "2026-09-07T15:16:28.814325Z",
        "status": "STABILITY_REVIEW_REQUIRED",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "source_model_run_id": "b" * 64,
        "source_feature_candidates_report_id": "c" * 64,
        "evaluation_scope": "TEST_ONLY",
        "preprocessing_reconstruction_scope": "TRAIN_ONLY",
        "selected_threshold": 0.5,
        "test_summary": segment(57584, 0.000384, 0.001041),
        "monthly_test_segments": [
            {"segment_id": "2024-01", "summary": segment(1800, -0.005)},
            {"segment_id": "2024-02", "summary": segment(1800, -0.003)},
            {"segment_id": "2024-03", "summary": segment(1800, -0.002)},
            {"segment_id": "2024-04", "summary": segment(1800, 0.002)},
        ],
        "direction_test_segments": {
            "LONG": segment(28792, 0.013547, 0.042277),
            "SHORT": segment(28792, -0.012778, -0.030586),
        },
        "volatility_test_segments": {
            "LOW": segment(19000, -0.002008, -0.002366),
            "MID": segment(19000, 0.000811, 0.001487),
            "HIGH": segment(19000, 0.000828, 0.005983),
        },
        "threshold_stability": [
            {"threshold": 0.45, "summary": segment(57584, 0.000554)},
            {"threshold": 0.5, "summary": segment(57584, 0.000384)},
            {"threshold": 0.55, "summary": segment(57584, -0.000515)},
        ],
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
        "promotion_allowed": False,
        "recommended_next_phase": "PHASE_54_WALK_FORWARD_RETRAINING_EXPERIMENTS",
    }


def test_walk_forward_experiments_prioritize_long_mid_high_variant():
    report = build_gc_walk_forward_experiments_report(
        stability_report(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert report["status"] == "WALK_FORWARD_EXPERIMENTS_READY"
    assert report["model_promotion_allowed"] is False
    assert report["research_execution_allowed"] is True
    assert report["source_stability_report_id"] == "a" * 64
    assert report["experiment_budget"]["max_windows"] == 8
    assert report["experiment_budget"]["epochs_per_window"] == 80
    assert report["experiment_budget"]["window_stride_months"] == 3
    assert report["recommended_experiments"][0]["experiment_id"] == "LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING"
    assert report["recommended_experiments"][0]["candidate_filter"]["directions"] == ["LONG"]
    assert report["recommended_experiments"][0]["candidate_filter"]["volatility_buckets"] == ["MID", "HIGH"]
    assert "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR" in {
        item["experiment_id"] for item in report["recommended_experiments"]
    }
    assert "MODEL_PROMOTION" in report["blocked_actions"]
    assert report["recommended_next_phase"] == "PHASE_55_EXECUTE_BOUNDED_WALK_FORWARD_RETRAINING"


def test_walk_forward_schema_rejects_model_promotion_allowed():
    run = build_gc_walk_forward_experiments_report(
        stability_report(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["model_promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

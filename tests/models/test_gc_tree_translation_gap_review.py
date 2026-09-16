from datetime import UTC, datetime

import pytest

from trading_system.models.gc_tree_translation_gap_review import build_gc_tree_translation_gap_review

FIXED_TIME = datetime(2026, 9, 7, 22, 0, tzinfo=UTC)


def walk_forward_run() -> dict:
    return {
        "run_id": "a" * 64,
        "run_version": "gc-bounded-walk-forward-retraining-run-0.1.0",
        "mode": "GC_BOUNDED_WALK_FORWARD_RETRAINING",
        "created_at": "2026-09-07T15:48:01.439725Z",
        "status": "WALK_FORWARD_RETRAINING_EXECUTED",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "source_experiment_report_id": "b" * 64,
        "source_feature_candidates_report_id": "c" * 64,
        "feature_names": ["ret_1", "direction_is_long", "atr_14_over_close", "of_delta_over_of_volume"],
        "experiment_budget": {"max_windows": 8},
        "experiment_results": [
            {
                "experiment_id": "MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING",
                "expected_value_use": "PRIMARY_RESEARCH",
                "valid_window_count": 1,
                "skipped_window_count": 7,
                "positive_test_window_count": 1,
                "aggregate_metrics": {"median_test_expected_r_per_candidate": 0.0013},
                "pass_gate": False,
            },
            {
                "experiment_id": "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR",
                "expected_value_use": "COMPARATOR",
                "valid_window_count": 8,
                "skipped_window_count": 0,
                "positive_test_window_count": 3,
                "aggregate_metrics": {"median_test_expected_r_per_candidate": -0.0013},
                "pass_gate": None,
            },
            {
                "experiment_id": "LONG_ONLY_WALK_FORWARD_RETRAINING",
                "expected_value_use": "PRIMARY_RESEARCH",
                "valid_window_count": 0,
                "skipped_window_count": 8,
                "positive_test_window_count": 0,
                "aggregate_metrics": {"median_test_expected_r_per_candidate": None},
                "pass_gate": None,
            },
        ],
        "decision_summary": {
            "best_primary_experiment_id": "MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING",
            "best_primary_median_test_expected_r_per_candidate": 0.0013,
            "comparator_median_test_expected_r_per_candidate": -0.0013,
            "promotion_review_allowed": False,
        },
        "research_execution_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": ["MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"],
        "recommended_next_phase": "PHASE_56_WALK_FORWARD_RESULTS_REVIEW",
    }


def test_tree_translation_review_requires_tree_gate_baseline_before_more_training():
    report = build_gc_tree_translation_gap_review(walk_forward_run(), created_at=FIXED_TIME).to_payload()

    assert report["status"] == "TREE_TRANSLATION_REDESIGN_REQUIRED"
    assert report["model_promotion_allowed"] is False
    assert report["additional_model_training_allowed"] is False
    assert report["source_walk_forward_run_id"] == "a" * 64
    assert "FLAT_MODEL_INSTEAD_OF_TREE_GATE_POLICY" in report["gap_codes"]
    assert "CANDIDATE_SELECTION_TOO_BROAD" in report["gap_codes"]
    assert "LABEL_TOO_NARROW_FOR_MANUAL_TRADING_PROCESS" in report["gap_codes"]
    assert report["tree_stage_coverage"]["VECTOR"]["current_coverage"] == "MISSING_AS_TYPED_TREE_STAGE"
    assert report["recommended_next_phase"] == "PHASE_57_TREE_GATE_BASELINE_AND_CANDIDATE_AUDIT"
    assert report["required_next_artifacts"][0] == "rule_only_tree_baseline"
    assert "MODEL_PROMOTION" in report["blocked_actions"]


def test_tree_translation_schema_rejects_model_promotion_allowed():
    run = build_gc_tree_translation_gap_review(walk_forward_run(), created_at=FIXED_TIME)
    payload = run.to_payload()
    payload["model_promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

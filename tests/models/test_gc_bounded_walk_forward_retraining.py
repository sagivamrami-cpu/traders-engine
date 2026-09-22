from dataclasses import replace
from datetime import UTC, datetime
import importlib.util
from pathlib import Path

import pytest

from trading_system.models.gc_bounded_walk_forward_retraining import run_gc_bounded_walk_forward_retraining
from trading_system.models.gc_walk_forward_experiments import build_gc_walk_forward_experiments_report

ROOT = Path(__file__).resolve().parents[2]
_STABILITY_SPEC = importlib.util.spec_from_file_location(
    "gc_normalized_model_stability_fixture",
    ROOT / "tests/models/test_gc_normalized_model_stability.py",
)
if _STABILITY_SPEC is None or _STABILITY_SPEC.loader is None:
    raise RuntimeError("normalized model stability fixture could not be loaded")
_STABILITY_MODULE = importlib.util.module_from_spec(_STABILITY_SPEC)
_STABILITY_SPEC.loader.exec_module(_STABILITY_MODULE)
feature_candidates = _STABILITY_MODULE.feature_candidates
row = _STABILITY_MODULE.row

_EXPERIMENTS_SPEC = importlib.util.spec_from_file_location(
    "gc_walk_forward_experiments_fixture",
    ROOT / "tests/models/test_gc_walk_forward_experiments.py",
)
if _EXPERIMENTS_SPEC is None or _EXPERIMENTS_SPEC.loader is None:
    raise RuntimeError("walk-forward experiments fixture could not be loaded")
_EXPERIMENTS_MODULE = importlib.util.module_from_spec(_EXPERIMENTS_SPEC)
_EXPERIMENTS_SPEC.loader.exec_module(_EXPERIMENTS_MODULE)
stability_report = _EXPERIMENTS_MODULE.stability_report

FIXED_TIME = datetime(2026, 9, 7, 21, 0, tzinfo=UTC)


def chronological_rows() -> list:
    rows = []
    index = 0
    for month in range(1, 7):
        split = "TEST" if month >= 4 else "TRAIN"
        for direction, outcome, ret_1, of_delta in (
            ("LONG", "TARGET_FIRST", 0.05, 8.0),
            ("LONG", "STOP_FIRST", -0.02, -2.0),
            ("SHORT", "TARGET_FIRST", 0.03, 4.0),
            ("SHORT", "STOP_FIRST", -0.04, -7.0),
        ):
            base = row(
                f"{month}-{direction}-{outcome}-{index}",
                outcome,
                split,
                index=index,
                direction=direction,
                ret_1=ret_1,
                of_delta=of_delta,
                close=1000.0 + month,
                    atr_14=2.0 if month == 1 else 6.0,
            )
            rows.append(
                replace(
                    base,
                    observation_time=datetime(2026, month, 15, tzinfo=UTC),
                    dataset_id="fixture-gc-dataset",
                )
            )
            index += 1
    return rows


def experiment_plan() -> dict:
    plan = build_gc_walk_forward_experiments_report(stability_report(), created_at=FIXED_TIME).to_payload()
    plan["experiment_budget"] = {
        **plan["experiment_budget"],
        "max_windows": 2,
        "window_stride_months": 1,
        "validation_months": 1,
        "epochs_per_window": 5,
        "minimum_train_rows_per_window": 2,
        "minimum_validation_rows_per_window": 2,
        "minimum_test_rows_per_window": 2,
        "threshold_grid": [0.45, 0.5, 0.55],
    }
    return plan


def test_bounded_walk_forward_retraining_executes_primary_and_comparator():
    report = run_gc_bounded_walk_forward_retraining(
        chronological_rows(),
        feature_candidates(),
        experiment_plan(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert report["status"] == "WALK_FORWARD_RETRAINING_EXECUTED"
    assert report["research_execution_allowed"] is False
    assert report["model_promotion_allowed"] is False
    assert report["source_experiment_report_id"] == experiment_plan()["report_id"]
    results = {item["experiment_id"]: item for item in report["experiment_results"]}
    assert "LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING" in results
    assert "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR" in results
    assert results["ALL_CANDIDATES_WALK_FORWARD_COMPARATOR"]["valid_window_count"] >= 1
    assert results["LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING"]["comparison_to_comparator"] is not None
    assert report["decision_summary"]["promotion_review_allowed"] is False
    assert "MODEL_PROMOTION" in report["blocked_actions"]


def test_bounded_walk_forward_schema_rejects_model_promotion_allowed():
    run = run_gc_bounded_walk_forward_retraining(
        chronological_rows(),
        feature_candidates(),
        experiment_plan(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["model_promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

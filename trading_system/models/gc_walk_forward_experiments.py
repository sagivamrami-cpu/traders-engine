from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_walk_forward_experiments_report.schema.json"
REPORT_VERSION = "gc-walk-forward-experiments-report-0.1.0"
MODE = "GC_WALK_FORWARD_RETRAINING_EXPERIMENTS"
BLOCKED_ACTIONS = [
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcWalkForwardExperimentsReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _expected_r(segment: dict[str, Any]) -> float | None:
    value = segment.get("expected_r_per_candidate")
    if value is None:
        return None
    return float(value)


def _segment_expected_r(report: dict[str, Any], *keys: str) -> float | None:
    current: Any = report
    for key in keys:
        current = current[key]
    return _expected_r(current)


def _high_threshold_expected_r(report: dict[str, Any]) -> float | None:
    threshold_rows = sorted(report["threshold_stability"], key=lambda item: float(item["threshold"]))
    if not threshold_rows:
        return None
    return _expected_r(threshold_rows[-1]["summary"])


def _negative_month_count(report: dict[str, Any]) -> int:
    return sum(
        1
        for item in report["monthly_test_segments"]
        if _expected_r(item["summary"]) is not None and float(item["summary"]["expected_r_per_candidate"]) < 0.0
    )


def _base_training_policy() -> dict[str, Any]:
    return {
        "window_mode": "EXPANDING_CHRONOLOGICAL_WALK_FORWARD",
        "train_scope": "all eligible observations strictly before the validation window",
        "validation_scope": "last three chronological months before each test window",
        "test_scope": "one forward chronological month, sampled every three months until max_windows is reached",
        "leakage_controls": [
            "no row at or after test window start may be used for that window training",
            "threshold is selected on the validation window only",
            "feature normalization is fitted on each window training rows only",
            "previous test labels may enter only later windows after their historical outcome horizon has passed",
        ],
    }


def _experiment(
    *,
    rank: int,
    experiment_id: str,
    objective: str,
    directions: list[str],
    volatility_buckets: list[str],
    expected_value_use: str,
    reason: str,
    source_findings: list[str],
) -> dict[str, Any]:
    return {
        "rank": rank,
        "experiment_id": experiment_id,
        "objective": objective,
        "candidate_filter": {
            "directions": directions,
            "volatility_buckets": volatility_buckets,
        },
        "training_policy": _base_training_policy(),
        "threshold_policy": "choose threshold per window from validation expected R, with trade-rate floor and no TEST peeking",
        "expected_value_use": expected_value_use,
        "promotion_use": "FORBIDDEN",
        "reason": reason,
        "source_findings": source_findings,
    }


def _stability_findings(stability_report: dict[str, Any]) -> dict[str, Any]:
    long_expected_r = _segment_expected_r(stability_report, "direction_test_segments", "LONG")
    short_expected_r = _segment_expected_r(stability_report, "direction_test_segments", "SHORT")
    low_expected_r = _segment_expected_r(stability_report, "volatility_test_segments", "LOW")
    mid_expected_r = _segment_expected_r(stability_report, "volatility_test_segments", "MID")
    high_expected_r = _segment_expected_r(stability_report, "volatility_test_segments", "HIGH")
    high_threshold_expected_r = _high_threshold_expected_r(stability_report)
    month_count = len(stability_report["monthly_test_segments"])
    negative_months = _negative_month_count(stability_report)
    return {
        "test_expected_r_per_candidate": _segment_expected_r(stability_report, "test_summary"),
        "test_expected_r_per_selected_trade": stability_report["test_summary"].get("expected_r_per_selected_trade"),
        "long_expected_r_per_candidate": long_expected_r,
        "short_expected_r_per_candidate": short_expected_r,
        "low_volatility_expected_r_per_candidate": low_expected_r,
        "mid_volatility_expected_r_per_candidate": mid_expected_r,
        "high_volatility_expected_r_per_candidate": high_expected_r,
        "high_threshold_expected_r_per_candidate": high_threshold_expected_r,
        "negative_month_count": negative_months,
        "total_month_count": month_count,
        "primary_read": (
            "Phase 53 shows a small positive total TEST result, carried mainly by LONG candidates; "
            "SHORT, LOW-volatility, and high-threshold behavior remain unstable."
        ),
    }


def _experiments() -> list[dict[str, Any]]:
    return [
        _experiment(
            rank=1,
            experiment_id="LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING",
            objective="test whether the strongest Phase 53 slice survives chronological retraining",
            directions=["LONG"],
            volatility_buckets=["MID", "HIGH"],
            expected_value_use="PRIMARY_RESEARCH",
            reason="LONG was positive while LOW volatility was negative, so the first serious variant should combine LONG with MID/HIGH volatility.",
            source_findings=[
                "LONG_TEST_EXPECTED_R_POSITIVE",
                "SHORT_TEST_EXPECTED_R_NEGATIVE",
                "LOW_VOLATILITY_EXPECTED_R_NEGATIVE",
                "MID_HIGH_VOLATILITY_EXPECTED_R_POSITIVE",
            ],
        ),
        _experiment(
            rank=2,
            experiment_id="LONG_ONLY_WALK_FORWARD_RETRAINING",
            objective="separate direction edge from volatility-regime filtering",
            directions=["LONG"],
            volatility_buckets=["LOW", "MID", "HIGH"],
            expected_value_use="PRIMARY_RESEARCH",
            reason="Phase 53 indicates LONG candidates carry the current positive result.",
            source_findings=["LONG_TEST_EXPECTED_R_POSITIVE", "SHORT_TEST_EXPECTED_R_NEGATIVE"],
        ),
        _experiment(
            rank=3,
            experiment_id="MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING",
            objective="test whether excluding LOW volatility improves all-direction behavior",
            directions=["LONG", "SHORT"],
            volatility_buckets=["MID", "HIGH"],
            expected_value_use="PRIMARY_RESEARCH",
            reason="LOW volatility was negative while MID and HIGH volatility were slightly positive.",
            source_findings=["LOW_VOLATILITY_EXPECTED_R_NEGATIVE", "MID_HIGH_VOLATILITY_EXPECTED_R_POSITIVE"],
        ),
        _experiment(
            rank=4,
            experiment_id="ALL_CANDIDATES_WALK_FORWARD_COMPARATOR",
            objective="provide the mandatory comparator against the current all-candidate static model",
            directions=["LONG", "SHORT"],
            volatility_buckets=["LOW", "MID", "HIGH"],
            expected_value_use="COMPARATOR",
            reason="Every filtered result needs an all-candidate walk-forward baseline.",
            source_findings=["STATIC_MODEL_OVERALL_TEST_RESULT_SMALL_POSITIVE"],
        ),
        _experiment(
            rank=5,
            experiment_id="SHORT_ONLY_DIAGNOSTIC_WALK_FORWARD_RETRAINING",
            objective="diagnose whether SHORT requires a separate model family or should remain excluded",
            directions=["SHORT"],
            volatility_buckets=["LOW", "MID", "HIGH"],
            expected_value_use="DIAGNOSTIC_ONLY",
            reason="SHORT was materially negative in Phase 53 and cannot be part of a promoted candidate without a separate fix.",
            source_findings=["SHORT_TEST_EXPECTED_R_NEGATIVE"],
        ),
        _experiment(
            rank=6,
            experiment_id="LOW_VOLATILITY_DIAGNOSTIC_WALK_FORWARD_RETRAINING",
            objective="diagnose whether LOW volatility should be filtered out or modeled separately",
            directions=["LONG", "SHORT"],
            volatility_buckets=["LOW"],
            expected_value_use="DIAGNOSTIC_ONLY",
            reason="LOW volatility was negative in Phase 53 and should not be mixed blindly into the primary model.",
            source_findings=["LOW_VOLATILITY_EXPECTED_R_NEGATIVE"],
        ),
    ]


def build_gc_walk_forward_experiments_report(
    stability_report: dict[str, Any],
    *,
    created_at: datetime,
) -> GcWalkForwardExperimentsReport:
    payload = {
        "report_id": "",
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "WALK_FORWARD_EXPERIMENTS_READY",
        "dataset_id": str(stability_report["dataset_id"]),
        "variant": str(stability_report.get("variant", "order_flow")),
        "source_stability_report_id": str(stability_report["report_id"]),
        "source_model_run_id": str(stability_report["source_model_run_id"]),
        "source_feature_candidates_report_id": str(stability_report["source_feature_candidates_report_id"]),
        "source_selected_threshold": float(stability_report["selected_threshold"]),
        "stability_findings": _stability_findings(stability_report),
        "experiment_budget": {
            "max_windows": 8,
            "window_stride_months": 3,
            "validation_months": 3,
            "epochs_per_window": 80,
            "minimum_train_rows_per_window": 50000,
            "minimum_validation_rows_per_window": 5000,
            "minimum_test_rows_per_window": 1000,
            "threshold_grid": [0.45, 0.475, 0.5, 0.525, 0.55],
        },
        "recommended_experiments": _experiments(),
        "decision_rules": [
            "promotion remains forbidden until a later human-approved promotion phase",
            "a primary experiment must beat the all-candidate walk-forward comparator on median expected R per candidate",
            "a primary experiment must have positive expected R per candidate in at least six evaluated windows",
            "no TEST window may be used for threshold selection of the same window",
            "SHORT and LOW-volatility diagnostic experiments cannot become promoted variants directly",
        ],
        "research_execution_allowed": True,
        "model_promotion_allowed": False,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_55_EXECUTE_BOUNDED_WALK_FORWARD_RETRAINING",
    }
    payload["report_id"] = _report_id(payload)
    return GcWalkForwardExperimentsReport(payload)

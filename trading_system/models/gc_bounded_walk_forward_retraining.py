from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Sequence

import numpy as np

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import utc_iso
from trading_system.models.first_real_gc_model import _fit_transform, _metrics, _raw_matrix, _sigmoid, _target_flags, _transform
from trading_system.models.gc_normalized_feature_model import materialize_normalized_features
from trading_system.models.readiness import included_rows

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_bounded_walk_forward_retraining_run.schema.json"
RUN_VERSION = "gc-bounded-walk-forward-retraining-run-0.1.0"
MODE = "GC_BOUNDED_WALK_FORWARD_RETRAINING"
BLOCKED_ACTIONS = [
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcBoundedWalkForwardRetrainingRun:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _run_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "run_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _feature_names(feature_candidates: dict[str, Any]) -> list[str]:
    return [str(name) for name in feature_candidates.get("next_model_feature_set", [])]


def _materialized_rows(
    rows: Sequence[CandidateTrainingRow],
    feature_candidates: dict[str, Any],
) -> list[CandidateTrainingRow]:
    return [
        replace(
            row,
            features=materialize_normalized_features(row, feature_candidates),
            feature_schema_version="gc-normalized-feature-schema-0.1.0",
        )
        for row in rows
    ]


def _month_start(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + months
    year = month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, 1, tzinfo=UTC)


def _eligible_test_months(rows: Sequence[CandidateTrainingRow], *, stride: int, max_windows: int) -> list[datetime]:
    months = sorted({_month_start(row.observation_time) for row in rows if row.split == "TEST"})
    return months[::stride][:max_windows]


def _fit_logistic(
    train_matrix: np.ndarray,
    y: np.ndarray,
    *,
    epochs: int,
    learning_rate: float = 0.08,
    l2: float = 0.01,
) -> tuple[np.ndarray, float]:
    weights = np.zeros(train_matrix.shape[1], dtype=float)
    positive_count = float(np.sum(y))
    negative_count = float(len(y) - positive_count)
    if positive_count == 0 or negative_count == 0:
        raise ValueError("INSUFFICIENT_TRAIN_TARGET_CLASSES")
    sample_weights = np.where(y == 1.0, len(y) / (2.0 * positive_count), len(y) / (2.0 * negative_count))
    intercept = float(math.log(positive_count / negative_count))
    normalizer = float(np.sum(sample_weights))

    for _ in range(epochs):
        probabilities = _sigmoid(train_matrix @ weights + intercept)
        errors = (probabilities - y) * sample_weights
        weights -= learning_rate * ((train_matrix.T @ errors) / normalizer + l2 * weights)
        intercept -= learning_rate * float(np.sum(errors) / normalizer)
    return weights, intercept


def _select_threshold(
    validation_rows: Sequence[CandidateTrainingRow],
    validation_probabilities: np.ndarray,
    threshold_grid: Sequence[float],
) -> float:
    min_selected = max(1, int(math.ceil(len(validation_rows) * 0.01)))
    best: tuple[float, float, float, float] | None = None
    for threshold in threshold_grid:
        selected = validation_probabilities >= float(threshold)
        if int(np.sum(selected)) < min_selected:
            continue
        metrics = _metrics(validation_rows, validation_probabilities, float(threshold), "validation")
        expected_r = float(metrics["validation_expected_r_per_candidate"] or 0.0)
        selected_rate = float(metrics["validation_selected_trade_rate"] or 0.0)
        precision = float(metrics["validation_target_precision"] or 0.0)
        candidate = (expected_r, selected_rate, precision, float(threshold))
        if best is None or candidate > best:
            best = candidate
    return best[3] if best is not None else 0.5


def _train_volatility_cutoffs(train_rows: Sequence[CandidateTrainingRow]) -> tuple[float, float]:
    values = [_numeric(row.features.get("atr_14_over_close")) for row in train_rows]
    clean = [value for value in values if value is not None]
    if not clean:
        return 0.0, 0.0
    return float(np.quantile(clean, 1 / 3)), float(np.quantile(clean, 2 / 3))


def _volatility_bucket(row: CandidateTrainingRow, cutoffs: tuple[float, float]) -> str:
    value = _numeric(row.features.get("atr_14_over_close"))
    low, high = cutoffs
    if value is None:
        return "HIGH"
    if value <= low:
        return "LOW"
    if value <= high:
        return "MID"
    return "HIGH"


def _filter_rows(
    rows: Sequence[CandidateTrainingRow],
    experiment: dict[str, Any],
    cutoffs: tuple[float, float],
) -> list[CandidateTrainingRow]:
    directions = set(experiment["candidate_filter"]["directions"])
    buckets = set(experiment["candidate_filter"]["volatility_buckets"])
    return [
        row
        for row in rows
        if row.direction in directions and _volatility_bucket(row, cutoffs) in buckets
    ]


def _skip_window(
    window_id: str,
    train_rows: int,
    validation_rows: int,
    test_rows: int,
    blocked_reasons: list[str],
) -> dict[str, Any]:
    return {
        "window_id": window_id,
        "status": "SKIPPED",
        "train_rows": train_rows,
        "validation_rows": validation_rows,
        "test_rows": test_rows,
        "selected_threshold": None,
        "metrics": {},
        "blocked_reasons": blocked_reasons,
    }


def _row_count_blockers(
    train_rows: Sequence[CandidateTrainingRow],
    validation_rows: Sequence[CandidateTrainingRow],
    test_rows: Sequence[CandidateTrainingRow],
    budget: dict[str, Any],
) -> list[str]:
    blockers = []
    if len(train_rows) < int(budget["minimum_train_rows_per_window"]):
        blockers.append("INSUFFICIENT_TRAIN_ROWS")
    if len(validation_rows) < int(budget["minimum_validation_rows_per_window"]):
        blockers.append("INSUFFICIENT_VALIDATION_ROWS")
    if len(test_rows) < int(budget["minimum_test_rows_per_window"]):
        blockers.append("INSUFFICIENT_TEST_ROWS")
    if len({row.outcome_class for row in train_rows}) < 2:
        blockers.append("INSUFFICIENT_TRAIN_TARGET_CLASSES")
    return blockers


def _run_window(
    rows: Sequence[CandidateTrainingRow],
    experiment: dict[str, Any],
    feature_names: Sequence[str],
    budget: dict[str, Any],
    month_start: datetime,
) -> dict[str, Any]:
    validation_start = _add_months(month_start, -int(budget["validation_months"]))
    test_end = _add_months(month_start, 1)
    train_base = [row for row in rows if row.observation_time < validation_start]
    validation_base = [row for row in rows if validation_start <= row.observation_time < month_start]
    test_base = [row for row in rows if month_start <= row.observation_time < test_end]
    cutoffs = _train_volatility_cutoffs(train_base)
    train_rows = _filter_rows(train_base, experiment, cutoffs)
    validation_rows = _filter_rows(validation_base, experiment, cutoffs)
    test_rows = _filter_rows(test_base, experiment, cutoffs)
    window_id = month_start.strftime("%Y-%m")
    blockers = _row_count_blockers(train_rows, validation_rows, test_rows, budget)
    if blockers:
        return _skip_window(window_id, len(train_rows), len(validation_rows), len(test_rows), blockers)

    train_matrix, means, stds = _fit_transform(_raw_matrix(train_rows, feature_names))
    validation_matrix = _transform(_raw_matrix(validation_rows, feature_names), means, stds)
    test_matrix = _transform(_raw_matrix(test_rows, feature_names), means, stds)
    try:
        weights, intercept = _fit_logistic(
            train_matrix,
            _target_flags(train_rows),
            epochs=int(budget["epochs_per_window"]),
        )
    except ValueError as error:
        return _skip_window(window_id, len(train_rows), len(validation_rows), len(test_rows), [str(error)])
    validation_probabilities = _sigmoid(validation_matrix @ weights + intercept)
    selected_threshold = _select_threshold(validation_rows, validation_probabilities, budget["threshold_grid"])
    test_probabilities = _sigmoid(test_matrix @ weights + intercept)
    return {
        "window_id": window_id,
        "status": "TRAINED",
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "test_rows": len(test_rows),
        "selected_threshold": float(selected_threshold),
        "metrics": {
            **_metrics(validation_rows, validation_probabilities, selected_threshold, "validation"),
            **_metrics(test_rows, test_probabilities, selected_threshold, "test"),
        },
        "blocked_reasons": [],
    }


def _metric_values(windows: Sequence[dict[str, Any]], metric: str) -> list[float]:
    values = []
    for window in windows:
        value = _numeric(window["metrics"].get(metric))
        if value is not None:
            values.append(value)
    return values


def _aggregate(windows: Sequence[dict[str, Any]]) -> dict[str, float | None]:
    valid = [window for window in windows if window["status"] == "TRAINED"]
    expected_r = _metric_values(valid, "test_expected_r_per_candidate")
    selected_expected_r = _metric_values(valid, "test_expected_r_per_selected_trade")
    selected_rates = _metric_values(valid, "test_selected_trade_rate")
    positive_count = sum(1 for value in expected_r if value > 0.0)
    return {
        "median_test_expected_r_per_candidate": float(median(expected_r)) if expected_r else None,
        "mean_test_expected_r_per_candidate": float(mean(expected_r)) if expected_r else None,
        "minimum_test_expected_r_per_candidate": float(min(expected_r)) if expected_r else None,
        "median_test_expected_r_per_selected_trade": float(median(selected_expected_r)) if selected_expected_r else None,
        "mean_test_selected_trade_rate": float(mean(selected_rates)) if selected_rates else None,
        "positive_test_window_rate": float(positive_count / len(expected_r)) if expected_r else None,
    }


def _experiment_result(
    rows: Sequence[CandidateTrainingRow],
    experiment: dict[str, Any],
    feature_names: Sequence[str],
    budget: dict[str, Any],
    months: Sequence[datetime],
) -> dict[str, Any]:
    windows = [_run_window(rows, experiment, feature_names, budget, month) for month in months]
    valid_count = sum(1 for window in windows if window["status"] == "TRAINED")
    positive_count = sum(
        1
        for window in windows
        if _numeric(window["metrics"].get("test_expected_r_per_candidate")) is not None
        and float(window["metrics"]["test_expected_r_per_candidate"]) > 0.0
    )
    blocked_reasons = []
    if valid_count == 0:
        blocked_reasons.append("NO_VALID_WALK_FORWARD_WINDOWS")
    return {
        "experiment_id": experiment["experiment_id"],
        "expected_value_use": experiment["expected_value_use"],
        "attempted_window_count": len(months),
        "valid_window_count": valid_count,
        "skipped_window_count": len(windows) - valid_count,
        "positive_test_window_count": positive_count,
        "aggregate_metrics": _aggregate(windows),
        "comparison_to_comparator": None,
        "windows": windows,
        "pass_gate": None,
        "blocked_reasons": blocked_reasons,
    }


def _add_comparisons(results: list[dict[str, Any]]) -> None:
    comparator = next((item for item in results if item["experiment_id"] == "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR"), None)
    comparator_median = None
    if comparator is not None:
        comparator_median = comparator["aggregate_metrics"]["median_test_expected_r_per_candidate"]
    for result in results:
        median_value = result["aggregate_metrics"]["median_test_expected_r_per_candidate"]
        if comparator is None or result is comparator or comparator_median is None or median_value is None:
            continue
        result["comparison_to_comparator"] = {
            "comparator_experiment_id": comparator["experiment_id"],
            "median_test_expected_r_per_candidate_delta": float(median_value - comparator_median),
        }
        if result["expected_value_use"] == "PRIMARY_RESEARCH":
            result["pass_gate"] = bool(
                result["valid_window_count"] >= 6
                and result["positive_test_window_count"] >= 6
                and median_value > comparator_median
            )


def _decision_summary(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    comparator = next((item for item in results if item["experiment_id"] == "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR"), None)
    comparator_median = None if comparator is None else comparator["aggregate_metrics"]["median_test_expected_r_per_candidate"]
    primary = [
        item
        for item in results
        if item["expected_value_use"] == "PRIMARY_RESEARCH"
        and item["aggregate_metrics"]["median_test_expected_r_per_candidate"] is not None
    ]
    best = max(primary, key=lambda item: item["aggregate_metrics"]["median_test_expected_r_per_candidate"], default=None)
    return {
        "best_primary_experiment_id": None if best is None else best["experiment_id"],
        "best_primary_median_test_expected_r_per_candidate": (
            None if best is None else best["aggregate_metrics"]["median_test_expected_r_per_candidate"]
        ),
        "comparator_median_test_expected_r_per_candidate": comparator_median,
        "promotion_review_allowed": False,
        "summary": "Bounded walk-forward research was executed; results require Phase 56 review before any further decision.",
    }


def run_gc_bounded_walk_forward_retraining(
    rows: Sequence[CandidateTrainingRow],
    feature_candidates: dict[str, Any],
    experiment_report: dict[str, Any],
    *,
    created_at: datetime,
) -> GcBoundedWalkForwardRetrainingRun:
    feature_names = _feature_names(feature_candidates)
    budget = dict(experiment_report["experiment_budget"])
    materialized = sorted(included_rows(_materialized_rows(rows, feature_candidates)), key=lambda row: row.observation_time)
    months = _eligible_test_months(materialized, stride=int(budget["window_stride_months"]), max_windows=int(budget["max_windows"]))
    results = [
        _experiment_result(materialized, experiment, feature_names, budget, months)
        for experiment in experiment_report["recommended_experiments"]
    ]
    _add_comparisons(results)
    status = "WALK_FORWARD_RETRAINING_EXECUTED" if any(item["valid_window_count"] for item in results) else "WALK_FORWARD_RETRAINING_BLOCKED"
    payload = {
        "run_id": "",
        "run_version": RUN_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": status,
        "dataset_id": str(experiment_report["dataset_id"]),
        "variant": str(experiment_report.get("variant", "order_flow")),
        "source_experiment_report_id": str(experiment_report["report_id"]),
        "source_feature_candidates_report_id": str(feature_candidates["report_id"]),
        "feature_names": feature_names,
        "experiment_budget": budget,
        "experiment_results": results,
        "decision_summary": _decision_summary(results),
        "research_execution_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_56_WALK_FORWARD_RESULTS_REVIEW",
    }
    payload["run_id"] = _run_id(payload)
    return GcBoundedWalkForwardRetrainingRun(payload)

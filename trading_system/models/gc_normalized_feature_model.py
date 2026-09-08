from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import utc_iso
from trading_system.models.first_real_gc_model import (
    THRESHOLD_SELECTION_METRIC,
    _dataset_value,
    _fit_logistic,
    _fit_transform,
    _gross_r,
    _label_version,
    _metrics,
    _numeric,
    _raw_matrix,
    _select_threshold,
    _target_flags,
    _transform,
)
from trading_system.models.readiness import TrainingPolicy, evaluate_training_readiness, included_rows

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_normalized_feature_model_run.schema.json"
RUN_VERSION = "gc-normalized-feature-model-run-0.1.0"
MODEL_TYPE = "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH"
MODEL_VERSION = "normalized-feature-logistic-research-0.1.0"
FORBIDDEN_FEATURES = {
    "close",
    "atr_14",
    "outcome_class",
    "net_return_r",
    "time_to_outcome_bars",
    "entry_price",
    "target_price",
    "stop_price",
    "risk_r",
}
DIRECTION_FEATURES = {"direction_is_long", "direction_is_short"}


@dataclass(frozen=True)
class GcNormalizedFeatureModelRun:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _run_id(payload: dict[str, Any]) -> str:
    stable_payload = {key: value for key, value in payload.items() if key != "run_id"}
    return hashlib.sha256(stable_json_dumps(stable_payload).encode("utf-8")).hexdigest()


def _safe_divide(numerator: Any, denominator: Any) -> float | None:
    numerator_value = _numeric(numerator)
    denominator_value = _numeric(denominator)
    if numerator_value is None or denominator_value is None or abs(denominator_value) <= 1e-12:
        return None
    return numerator_value / denominator_value


def _candidate_feature_names(feature_candidates: dict[str, Any]) -> list[str]:
    return [str(name) for name in feature_candidates.get("next_model_feature_set", [])]


def _forbidden_candidate_features(feature_candidates: dict[str, Any]) -> list[str]:
    return sorted(set(_candidate_feature_names(feature_candidates)) & FORBIDDEN_FEATURES)


def _candidate_gate_blockers(feature_candidates: dict[str, Any]) -> list[str]:
    blockers = []
    if feature_candidates.get("status") != "NORMALIZED_FEATURE_CANDIDATES_READY":
        blockers.append("FEATURE_CANDIDATES_NOT_READY")
    if feature_candidates.get("research_training_allowed") is not True:
        blockers.append("FEATURE_CANDIDATES_NOT_RESEARCH_TRAINABLE")
    if feature_candidates.get("model_promotion_allowed") is not False:
        blockers.append("FEATURE_CANDIDATES_PROMOTION_BOUNDARY_INVALID")
    for feature in _forbidden_candidate_features(feature_candidates):
        blockers.append(f"FORBIDDEN_FEATURE_PRESENT:{feature}")
    return blockers


def materialize_normalized_features(
    row: CandidateTrainingRow,
    feature_candidates: dict[str, Any],
) -> dict[str, float | None]:
    source = row.features
    requested = set(_candidate_feature_names(feature_candidates))
    features: dict[str, float | None] = {}

    for name in ("ret_1", "ret_4", "ret_8", "ret_14", "range_over_atr"):
        if name in requested:
            features[name] = _numeric(source.get(name))

    ratio_values = {
        "atr_14_over_close": _safe_divide(source.get("atr_14"), source.get("close")),
        "of_delta_over_of_volume": _safe_divide(source.get("of_delta"), source.get("of_volume")),
        "of_delta_sum_14_over_of_volume_sum_14": _safe_divide(
            source.get("of_delta_sum_14"),
            source.get("of_volume_sum_14"),
        ),
        "of_trades_per_minute": _safe_divide(source.get("of_trades"), source.get("of_minutes_present")),
        "of_volume_per_trade": _safe_divide(source.get("of_volume"), source.get("of_trades")),
        "of_volume_vs_14bar_avg": _safe_divide(
            source.get("of_volume"),
            _safe_divide(source.get("of_volume_sum_14"), 14.0),
        ),
        "of_trades_vs_14bar_avg": _safe_divide(
            source.get("of_trades"),
            _safe_divide(source.get("of_trades_sum_14"), 14.0),
        ),
    }
    for name, value in ratio_values.items():
        if name in requested:
            features[name] = value
    return features


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


def _base_payload(
    rows: Sequence[CandidateTrainingRow],
    policy: TrainingPolicy,
    feature_candidates: dict[str, Any],
    previous_model_run: dict[str, Any],
    baseline_run: dict[str, Any],
    created_at: datetime,
    *,
    status: str,
    split_summary: dict[str, int],
    class_distribution: dict[str, int],
    blocked_reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "run_id": "",
        "run_version": RUN_VERSION,
        "status": status,
        "dataset_id": _dataset_value(rows, "dataset_id", str(feature_candidates.get("dataset_id", "UNKNOWN_DATASET"))),
        "dataset_version": _dataset_value(rows, "dataset_version", "UNKNOWN_DATASET_VERSION"),
        "model_type": MODEL_TYPE,
        "model_version": None if status == "BLOCKED" else MODEL_VERSION,
        "created_at": utc_iso(created_at),
        "training_policy_version": policy.version,
        "feature_schema_version": "gc-normalized-feature-schema-0.1.0",
        "label_version": _label_version(rows),
        "source_feature_candidates_report_id": feature_candidates.get("report_id"),
        "source_feature_candidates_report_version": feature_candidates.get("report_version"),
        "source_previous_model_run_id": previous_model_run.get("run_id"),
        "source_baseline_run_id": baseline_run.get("run_id"),
        "split_summary": dict(sorted(split_summary.items())),
        "class_distribution": dict(sorted(class_distribution.items())),
        "fit_scope": "TRAIN_ONLY",
        "selection_scope": "VALIDATION_ONLY",
        "final_evaluation_scope": "TEST_ONLY",
        "feature_names": [],
        "excluded_raw_features": list(feature_candidates.get("excluded_raw_features", [])),
        "training_parameters": {},
        "selected_threshold": None,
        "threshold_selection_metric": THRESHOLD_SELECTION_METRIC,
        "intercept": None,
        "coefficients": {},
        "metrics": {},
        "comparison_metrics": {
            "previous_model_run_id": previous_model_run.get("run_id"),
            "baseline_run_id": baseline_run.get("run_id"),
        },
        "blocked_reasons": list(blocked_reasons),
        "promotion_allowed": False,
    }


def _metric_delta(current_metrics: dict[str, Any], reference_metrics: dict[str, Any], name: str) -> float | None:
    current = _numeric(current_metrics.get(name))
    reference = _numeric(reference_metrics.get(name))
    if current is None or reference is None:
        return None
    return current - reference


def _comparison_metrics(
    metrics: dict[str, Any],
    previous_model_run: dict[str, Any],
    baseline_run: dict[str, Any],
) -> dict[str, Any]:
    previous_metrics = dict(previous_model_run.get("metrics", {}))
    baseline_metrics = dict(baseline_run.get("metrics", {}))
    return {
        "previous_model_run_id": previous_model_run.get("run_id"),
        "baseline_run_id": baseline_run.get("run_id"),
        "validation_accuracy_delta_vs_previous_model": _metric_delta(metrics, previous_metrics, "validation_accuracy"),
        "test_accuracy_delta_vs_previous_model": _metric_delta(metrics, previous_metrics, "test_accuracy"),
        "validation_expected_r_per_candidate_delta_vs_previous_model": _metric_delta(
            metrics,
            previous_metrics,
            "validation_expected_r_per_candidate",
        ),
        "test_expected_r_per_candidate_delta_vs_previous_model": _metric_delta(
            metrics,
            previous_metrics,
            "test_expected_r_per_candidate",
        ),
        "validation_accuracy_delta_vs_baseline": _metric_delta(metrics, baseline_metrics, "validation_accuracy"),
        "test_accuracy_delta_vs_baseline": _metric_delta(metrics, baseline_metrics, "test_accuracy"),
    }


def train_gc_normalized_feature_model(
    rows: Sequence[CandidateTrainingRow],
    policy: TrainingPolicy,
    feature_candidates: dict[str, Any],
    previous_model_run: dict[str, Any],
    baseline_run: dict[str, Any],
    *,
    created_at: datetime,
) -> GcNormalizedFeatureModelRun:
    rows = list(rows)
    readiness = evaluate_training_readiness(rows, policy)
    gate_blockers = _candidate_gate_blockers(feature_candidates)
    base = _base_payload(
        rows,
        policy,
        feature_candidates,
        previous_model_run,
        baseline_run,
        created_at,
        status="TRAINED" if readiness.ready and not gate_blockers else "BLOCKED",
        split_summary=readiness.split_summary,
        class_distribution=readiness.class_distribution,
        blocked_reasons=[*readiness.blocked_reasons, *gate_blockers],
    )
    if base["status"] == "BLOCKED":
        base["run_id"] = _run_id(base)
        return GcNormalizedFeatureModelRun(base)

    feature_names = _candidate_feature_names(feature_candidates)
    eligible = included_rows(_materialized_rows(rows, feature_candidates))
    train_rows = [row for row in eligible if row.split == "TRAIN"]
    validation_rows = [row for row in eligible if row.split == "VALIDATION"]
    test_rows = [row for row in eligible if row.split == "TEST"]
    train_raw = _raw_matrix(train_rows, feature_names)
    validation_raw = _raw_matrix(validation_rows, feature_names)
    test_raw = _raw_matrix(test_rows, feature_names)
    train_matrix, means, stds = _fit_transform(train_raw)
    validation_matrix = _transform(validation_raw, means, stds)
    test_matrix = _transform(test_raw, means, stds)
    train_target = _target_flags(train_rows)

    try:
        weights, intercept, training_parameters = _fit_logistic(train_matrix, train_target)
    except ValueError as error:
        base["status"] = "BLOCKED"
        base["model_version"] = None
        base["blocked_reasons"] = [str(error)]
        base["run_id"] = _run_id(base)
        return GcNormalizedFeatureModelRun(base)

    validation_probabilities = 1.0 / (1.0 + np.exp(-np.clip(validation_matrix @ weights + intercept, -40.0, 40.0)))
    test_probabilities = 1.0 / (1.0 + np.exp(-np.clip(test_matrix @ weights + intercept, -40.0, 40.0)))
    selected_threshold = _select_threshold(validation_rows, validation_probabilities)
    metrics = {
        **_metrics(validation_rows, validation_probabilities, selected_threshold, "validation"),
        **_metrics(test_rows, test_probabilities, selected_threshold, "test"),
    }
    metrics["test_expected_r_if_all_candidates"] = (
        float(sum(_gross_r(row) for row in test_rows) / len(test_rows)) if test_rows else None
    )
    payload = {
        **base,
        "feature_names": feature_names,
        "training_parameters": {
            **training_parameters,
            "feature_candidate_gate": "PHASE_51_NORMALIZED_FEATURE_CANDIDATES",
            "feature_materialization": "ZERO_SAFE_NORMALIZED_RATIOS",
        },
        "selected_threshold": float(selected_threshold),
        "intercept": float(intercept),
        "coefficients": {name: float(weight) for name, weight in zip(feature_names, weights)},
        "metrics": dict(sorted(metrics.items())),
        "comparison_metrics": _comparison_metrics(metrics, previous_model_run, baseline_run),
        "blocked_reasons": [],
    }
    payload["run_id"] = _run_id(payload)
    return GcNormalizedFeatureModelRun(payload)

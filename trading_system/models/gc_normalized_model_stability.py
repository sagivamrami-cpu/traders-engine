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
from trading_system.models.first_real_gc_model import _fit_transform, _metrics, _raw_matrix, _sigmoid, _transform
from trading_system.models.gc_normalized_feature_model import materialize_normalized_features
from trading_system.models.readiness import included_rows

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_normalized_model_stability_report.schema.json"
REPORT_VERSION = "gc-normalized-model-stability-report-0.1.0"
MODE = "GC_NORMALIZED_MODEL_STABILITY"
BLOCKED_ACTIONS = [
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcNormalizedModelStabilityReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


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


def _score_rows(
    rows: Sequence[CandidateTrainingRow],
    feature_candidates: dict[str, Any],
    model_run: dict[str, Any],
) -> tuple[list[CandidateTrainingRow], np.ndarray]:
    feature_names = [str(name) for name in model_run["feature_names"]]
    ordered = included_rows(_materialized_rows(rows, feature_candidates))
    train_rows = [row for row in ordered if row.split == "TRAIN"]
    test_rows = [row for row in ordered if row.split == "TEST"]
    train_matrix, means, stds = _fit_transform(_raw_matrix(train_rows, feature_names))
    if train_matrix.shape[0] == 0:
        raise ValueError("TRAIN_ROWS_REQUIRED_FOR_PREPROCESSING_RECONSTRUCTION")
    test_matrix = _transform(_raw_matrix(test_rows, feature_names), means, stds)
    weights = np.array([float(model_run["coefficients"][name]) for name in feature_names], dtype=float)
    probabilities = _sigmoid(test_matrix @ weights + float(model_run["intercept"]))
    return test_rows, probabilities


def _empty_segment() -> dict[str, float | int | None]:
    return {
        "rows": 0,
        "accuracy": None,
        "target_precision": None,
        "target_recall": None,
        "selected_trade_rate": None,
        "expected_r_per_candidate": None,
        "expected_r_per_selected_trade": None,
    }


def _segment_summary(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float | int | None]:
    if not rows:
        return _empty_segment()
    metrics = _metrics(rows, probabilities, threshold, "segment")
    return {
        "rows": len(rows),
        "accuracy": metrics["segment_accuracy"],
        "target_precision": metrics["segment_target_precision"],
        "target_recall": metrics["segment_target_recall"],
        "selected_trade_rate": metrics["segment_selected_trade_rate"],
        "expected_r_per_candidate": metrics["segment_expected_r_per_candidate"],
        "expected_r_per_selected_trade": metrics["segment_expected_r_per_selected_trade"],
    }


def _subset(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    predicate: Any,
) -> tuple[list[CandidateTrainingRow], np.ndarray]:
    indexes = [index for index, row in enumerate(rows) if predicate(row)]
    return [rows[index] for index in indexes], probabilities[indexes]


def _monthly_segments(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    threshold: float,
) -> list[dict[str, Any]]:
    months = sorted({row.observation_time.strftime("%Y-%m") for row in rows})
    segments = []
    for month in months:
        segment_rows, segment_probabilities = _subset(rows, probabilities, lambda row, month=month: row.observation_time.strftime("%Y-%m") == month)
        segments.append({"segment_id": month, "summary": _segment_summary(segment_rows, segment_probabilities, threshold)})
    return segments


def _direction_segments(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, dict[str, float | int | None]]:
    result = {}
    for direction in ("LONG", "SHORT"):
        segment_rows, segment_probabilities = _subset(rows, probabilities, lambda row, direction=direction: row.direction == direction)
        result[direction] = _segment_summary(segment_rows, segment_probabilities, threshold)
    return result


def _train_volatility_cutoffs(
    rows: Sequence[CandidateTrainingRow],
    feature_candidates: dict[str, Any],
) -> tuple[float, float]:
    train_values = [
        float(materialized.features["atr_14_over_close"])
        for materialized in _materialized_rows(rows, feature_candidates)
        if materialized.split == "TRAIN" and materialized.features.get("atr_14_over_close") is not None
    ]
    if not train_values:
        return 0.0, 0.0
    return float(np.quantile(train_values, 1 / 3)), float(np.quantile(train_values, 2 / 3))


def _volatility_bucket(row: CandidateTrainingRow, low: float, high: float) -> str:
    value = row.features.get("atr_14_over_close")
    if value is None:
        return "HIGH"
    if float(value) <= low:
        return "LOW"
    if float(value) <= high:
        return "MID"
    return "HIGH"


def _volatility_segments(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    threshold: float,
    cutoffs: tuple[float, float],
) -> dict[str, dict[str, float | int | None]]:
    low, high = cutoffs
    result = {}
    for bucket in ("LOW", "MID", "HIGH"):
        segment_rows, segment_probabilities = _subset(rows, probabilities, lambda row, bucket=bucket: _volatility_bucket(row, low, high) == bucket)
        result[bucket] = _segment_summary(segment_rows, segment_probabilities, threshold)
    return result


def _threshold_stability(
    rows: Sequence[CandidateTrainingRow],
    probabilities: np.ndarray,
    threshold: float,
) -> list[dict[str, Any]]:
    thresholds = [max(0.0, threshold - 0.05), threshold, min(1.0, threshold + 0.05)]
    return [
        {"threshold": float(value), "summary": _segment_summary(rows, probabilities, float(value))}
        for value in thresholds
    ]


def build_gc_normalized_model_stability_report(
    rows: Sequence[CandidateTrainingRow],
    feature_candidates: dict[str, Any],
    model_run: dict[str, Any],
    *,
    created_at: datetime,
) -> GcNormalizedModelStabilityReport:
    test_rows, probabilities = _score_rows(rows, feature_candidates, model_run)
    threshold = float(model_run["selected_threshold"])
    cutoffs = _train_volatility_cutoffs(rows, feature_candidates)
    payload = {
        "report_id": "",
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "STABILITY_REVIEW_REQUIRED",
        "dataset_id": str(model_run["dataset_id"]),
        "variant": str(feature_candidates.get("variant", "order_flow")),
        "source_model_run_id": str(model_run["run_id"]),
        "source_feature_candidates_report_id": str(feature_candidates["report_id"]),
        "evaluation_scope": "TEST_ONLY",
        "preprocessing_reconstruction_scope": "TRAIN_ONLY",
        "selected_threshold": threshold,
        "test_summary": _segment_summary(test_rows, probabilities, threshold),
        "monthly_test_segments": _monthly_segments(test_rows, probabilities, threshold),
        "direction_test_segments": _direction_segments(test_rows, probabilities, threshold),
        "volatility_test_segments": _volatility_segments(test_rows, probabilities, threshold, cutoffs),
        "threshold_stability": _threshold_stability(test_rows, probabilities, threshold),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "promotion_allowed": False,
        "recommended_next_phase": "PHASE_54_WALK_FORWARD_RETRAINING_EXPERIMENTS",
    }
    payload["report_id"] = _report_id(payload)
    return GcNormalizedModelStabilityReport(payload)

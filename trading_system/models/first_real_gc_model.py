from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import utc_iso
from trading_system.models.readiness import TrainingPolicy, evaluate_training_readiness, included_rows

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_first_real_model_run.schema.json"
RUN_VERSION = "gc-first-real-model-run-0.1.0"
MODEL_TYPE = "REGULARIZED_LOGISTIC_RESEARCH_BASELINE"
MODEL_VERSION = "regularized-logistic-research-baseline-0.1.0"
THRESHOLD_SELECTION_METRIC = "validation_expected_r_per_candidate"
APPROVED_FEATURE_NAMES = frozenset(
    {
        "close",
        "atr_14",
        "ret_1",
        "ret_4",
        "ret_8",
        "ret_14",
        "range_over_atr",
        "volume_30m",
        "seconds_with_trades",
        "of_volume",
        "of_delta",
        "of_trades",
        "of_minutes_present",
        "of_volume_sum_14",
        "of_delta_sum_14",
        "of_trades_sum_14",
    }
)


@dataclass(frozen=True)
class FirstRealGcModelRun:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _run_id(payload: dict[str, Any]) -> str:
    stable_payload = {key: value for key, value in payload.items() if key != "run_id"}
    return hashlib.sha256(stable_json_dumps(stable_payload).encode("utf-8")).hexdigest()


def _dataset_value(rows: Sequence[CandidateTrainingRow], attr: str, fallback: str) -> str:
    return str(getattr(rows[0], attr)) if rows else fallback


def _label_version(rows: Sequence[CandidateTrainingRow]) -> str | None:
    return next((str(row.label_version) for row in rows if row.label_version), None)


def _base_payload(
    rows: Sequence[CandidateTrainingRow],
    policy: TrainingPolicy,
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
        "dataset_id": _dataset_value(rows, "dataset_id", "UNKNOWN_DATASET"),
        "dataset_version": _dataset_value(rows, "dataset_version", "UNKNOWN_DATASET_VERSION"),
        "model_type": MODEL_TYPE,
        "model_version": None if status == "BLOCKED" else MODEL_VERSION,
        "created_at": utc_iso(created_at),
        "training_policy_version": policy.version,
        "feature_schema_version": _dataset_value(rows, "feature_schema_version", "UNKNOWN_FEATURE_SCHEMA"),
        "label_version": _label_version(rows),
        "split_summary": dict(sorted(split_summary.items())),
        "class_distribution": dict(sorted(class_distribution.items())),
        "fit_scope": "TRAIN_ONLY",
        "selection_scope": "VALIDATION_ONLY",
        "final_evaluation_scope": "TEST_ONLY",
        "feature_names": [],
        "training_parameters": {},
        "selected_threshold": None,
        "threshold_selection_metric": THRESHOLD_SELECTION_METRIC,
        "intercept": None,
        "coefficients": {},
        "metrics": {},
        "blocked_reasons": list(blocked_reasons),
        "promotion_allowed": False,
    }


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


def _feature_names(train_rows: Sequence[CandidateTrainingRow]) -> list[str]:
    names = {
        key
        for row in train_rows
        for key, value in row.features.items()
        if _numeric(value) is not None
    }
    return [*sorted(names), "direction_is_long", "direction_is_short"]


def _forbidden_feature_names(rows: Sequence[CandidateTrainingRow]) -> list[str]:
    return sorted(
        {
            str(key)
            for row in rows
            for key in row.features
            if str(key) not in APPROVED_FEATURE_NAMES
        }
    )


def _raw_matrix(rows: Sequence[CandidateTrainingRow], feature_names: Sequence[str]) -> np.ndarray:
    matrix = np.empty((len(rows), len(feature_names)), dtype=float)
    for row_index, row in enumerate(rows):
        for column_index, name in enumerate(feature_names):
            if name == "direction_is_long":
                value = 1.0 if row.direction == "LONG" else 0.0
            elif name == "direction_is_short":
                value = 1.0 if row.direction == "SHORT" else 0.0
            else:
                value = _numeric(row.features.get(name))
            matrix[row_index, column_index] = np.nan if value is None else value
    return matrix


def _fit_transform(train_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = np.nanmean(train_matrix, axis=0)
    means = np.where(np.isnan(means), 0.0, means)
    imputed = np.where(np.isnan(train_matrix), means, train_matrix)
    stds = np.std(imputed, axis=0)
    stds = np.where(stds <= 1e-12, 1.0, stds)
    return (imputed - means) / stds, means, stds


def _transform(matrix: np.ndarray, means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    imputed = np.where(np.isnan(matrix), means, matrix)
    return (imputed - means) / stds


def _target_flags(rows: Sequence[CandidateTrainingRow]) -> np.ndarray:
    return np.array([1.0 if row.outcome_class == "TARGET_FIRST" else 0.0 for row in rows], dtype=float)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _fit_logistic(train_matrix: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, dict[str, float | int | str]]:
    epochs = 220
    learning_rate = 0.08
    l2 = 0.01
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

    return weights, intercept, {
        "solver": "in_repo_batch_gradient_descent",
        "epochs": epochs,
        "learning_rate": learning_rate,
        "l2": l2,
        "target_class": "TARGET_FIRST",
        "negative_classes": "STOP_FIRST_OR_EXPIRED",
    }


def _gross_r(row: CandidateTrainingRow) -> float:
    explicit_return = _numeric(row.outcome_return_r)
    if explicit_return is not None:
        return explicit_return
    if row.outcome_class == "TARGET_FIRST":
        return 1.0
    if row.outcome_class == "STOP_FIRST":
        return -1.0
    return 0.0


def _balanced_accuracy(rows: Sequence[CandidateTrainingRow], predictions: Sequence[str]) -> float | None:
    classes = sorted({str(row.outcome_class) for row in rows if row.outcome_class is not None})
    if not classes:
        return None
    recalls = []
    for outcome_class in classes:
        total = sum(1 for row in rows if row.outcome_class == outcome_class)
        correct = sum(1 for row, prediction in zip(rows, predictions) if row.outcome_class == outcome_class and prediction == outcome_class)
        recalls.append(correct / total if total else 0.0)
    return float(sum(recalls) / len(recalls))


def _metrics(rows: Sequence[CandidateTrainingRow], probabilities: np.ndarray, threshold: float, prefix: str) -> dict[str, float | None]:
    if not rows:
        return {
            f"{prefix}_accuracy": None,
            f"{prefix}_balanced_accuracy": None,
            f"{prefix}_binary_accuracy": None,
            f"{prefix}_target_precision": None,
            f"{prefix}_target_recall": None,
            f"{prefix}_selected_trade_rate": None,
            f"{prefix}_expected_r_per_candidate": None,
            f"{prefix}_expected_r_per_selected_trade": None,
        }
    selected = probabilities >= threshold
    predictions = ["TARGET_FIRST" if value else "STOP_FIRST" for value in selected]
    actual_target = np.array([row.outcome_class == "TARGET_FIRST" for row in rows], dtype=bool)
    correct = sum(1 for row, prediction in zip(rows, predictions) if row.outcome_class == prediction)
    true_positive = int(np.sum(selected & actual_target))
    selected_count = int(np.sum(selected))
    target_count = int(np.sum(actual_target))
    strategy_returns = [_gross_r(row) if is_selected else 0.0 for row, is_selected in zip(rows, selected)]
    selected_returns = [_gross_r(row) for row, is_selected in zip(rows, selected) if is_selected]
    return {
        f"{prefix}_accuracy": float(correct / len(rows)),
        f"{prefix}_balanced_accuracy": _balanced_accuracy(rows, predictions),
        f"{prefix}_binary_accuracy": float(np.mean(selected == actual_target)),
        f"{prefix}_target_precision": float(true_positive / selected_count) if selected_count else None,
        f"{prefix}_target_recall": float(true_positive / target_count) if target_count else None,
        f"{prefix}_selected_trade_rate": float(selected_count / len(rows)),
        f"{prefix}_expected_r_per_candidate": float(sum(strategy_returns) / len(rows)),
        f"{prefix}_expected_r_per_selected_trade": float(sum(selected_returns) / len(selected_returns)) if selected_returns else None,
    }


def _select_threshold(validation_rows: Sequence[CandidateTrainingRow], probabilities: np.ndarray) -> float:
    thresholds = np.linspace(0.05, 0.95, 91)
    min_selected = max(1, int(math.ceil(len(validation_rows) * 0.01)))
    best: tuple[float, float, float, float] | None = None
    for threshold in thresholds:
        selected = probabilities >= threshold
        if int(np.sum(selected)) < min_selected:
            continue
        metrics = _metrics(validation_rows, probabilities, float(threshold), "validation")
        expected_r = float(metrics["validation_expected_r_per_candidate"] or 0.0)
        accuracy = float(metrics["validation_accuracy"] or 0.0)
        precision = float(metrics["validation_target_precision"] or 0.0)
        candidate = (expected_r, accuracy, precision, float(threshold))
        if best is None or candidate > best:
            best = candidate
    if best is None:
        return 0.5
    return best[3]


def train_first_real_gc_model(
    rows: Sequence[CandidateTrainingRow],
    policy: TrainingPolicy,
    *,
    created_at: datetime,
) -> FirstRealGcModelRun:
    rows = list(rows)
    readiness = evaluate_training_readiness(rows, policy)
    base = _base_payload(
        rows,
        policy,
        created_at,
        status="TRAINED" if readiness.ready else "BLOCKED",
        split_summary=readiness.split_summary,
        class_distribution=readiness.class_distribution,
        blocked_reasons=readiness.blocked_reasons,
    )
    if not readiness.ready:
        base["run_id"] = _run_id(base)
        return FirstRealGcModelRun(base)

    eligible = included_rows(rows)
    forbidden_features = _forbidden_feature_names(eligible)
    if forbidden_features:
        base["status"] = "BLOCKED"
        base["model_version"] = None
        base["blocked_reasons"] = [f"FORBIDDEN_FEATURE_PRESENT:{name}" for name in forbidden_features]
        base["run_id"] = _run_id(base)
        return FirstRealGcModelRun(base)

    train_rows = [row for row in eligible if row.split == "TRAIN"]
    validation_rows = [row for row in eligible if row.split == "VALIDATION"]
    test_rows = [row for row in eligible if row.split == "TEST"]
    feature_names = _feature_names(train_rows)
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
        return FirstRealGcModelRun(base)

    validation_probabilities = _sigmoid(validation_matrix @ weights + intercept)
    test_probabilities = _sigmoid(test_matrix @ weights + intercept)
    selected_threshold = _select_threshold(validation_rows, validation_probabilities)
    metrics = {
        **_metrics(validation_rows, validation_probabilities, selected_threshold, "validation"),
        **_metrics(test_rows, test_probabilities, selected_threshold, "test"),
    }
    payload = {
        **base,
        "feature_names": list(feature_names),
        "training_parameters": training_parameters,
        "selected_threshold": float(selected_threshold),
        "intercept": float(intercept),
        "coefficients": {name: float(weight) for name, weight in zip(feature_names, weights)},
        "metrics": dict(sorted(metrics.items())),
        "blocked_reasons": [],
    }
    payload["run_id"] = _run_id(payload)
    return FirstRealGcModelRun(payload)

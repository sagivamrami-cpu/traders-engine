from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.evaluation.contracts import EvaluationWindow, ModelEvaluationReport
from trading_system.evaluation.metrics import accuracy, brier_score_target_first, expected_calibration_error
from trading_system.evaluation.predictions import prediction_from_majority_baseline


@dataclass(frozen=True)
class WalkForwardPolicy:
    version: str
    min_train_size: int
    validation_size: int
    min_windows: int
    calibration_bin_count: int


def load_walk_forward_policy(path: Path) -> WalkForwardPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return WalkForwardPolicy(
        version=data["version"],
        min_train_size=int(data["window_policy"]["min_train_size"]),
        validation_size=int(data["window_policy"]["validation_size"]),
        min_windows=int(data["window_policy"]["min_windows"]),
        calibration_bin_count=int(data["calibration"]["bin_count"]),
    )


def included_rows(rows: list[CandidateTrainingRow]) -> list[CandidateTrainingRow]:
    return sorted(
        [
            row
            for row in rows
            if row.included_in_training
            and row.outcome_class is not None
            and row.label_quality != "EXCLUDED_FROM_TRAINING"
        ],
        key=lambda row: (row.observation_time, row.row_id),
    )


def build_expanding_windows(
    rows: list[CandidateTrainingRow],
    *,
    min_train_size: int,
    validation_size: int,
) -> list[EvaluationWindow]:
    if min_train_size <= 0 or validation_size <= 0:
        raise ValueError("window sizes must be positive")
    ordered = included_rows(rows)
    windows: list[EvaluationWindow] = []
    start = min_train_size
    while start + validation_size <= len(ordered):
        train_rows = ordered[:start]
        validation_rows = ordered[start : start + validation_size]
        if train_rows[-1].observation_time >= validation_rows[0].observation_time:
            raise ValueError("walk-forward windows must be chronological")
        windows.append(
            EvaluationWindow(
                window_id=f"wf-{len(windows) + 1}",
                train_row_ids=tuple(row.row_id for row in train_rows),
                validation_row_ids=tuple(row.row_id for row in validation_rows),
                metrics={},
            )
        )
        start += validation_size
    return windows


def _majority_class(rows: list[CandidateTrainingRow]) -> str:
    counts = Counter(row.outcome_class for row in rows)
    return str(sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0][0])


def _report_id(training_run_id: str, rows: list[CandidateTrainingRow], created_at: datetime, policy: WalkForwardPolicy) -> str:
    payload = {
        "training_run_id": training_run_id,
        "rows": [row.row_id for row in rows],
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "policy": policy.version,
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def evaluate_majority_baseline_walk_forward(
    rows: list[CandidateTrainingRow],
    policy: WalkForwardPolicy,
    *,
    training_run_id: str,
    model_version: str,
    created_at: datetime,
) -> ModelEvaluationReport:
    ordered = included_rows(rows)
    windows = build_expanding_windows(
        ordered,
        min_train_size=policy.min_train_size,
        validation_size=policy.validation_size,
    )
    evaluated_windows: list[EvaluationWindow] = []
    all_probabilities: list[float] = []
    all_actual: list[str] = []
    accuracies: list[float] = []
    briers: list[float] = []

    for window in windows:
        by_id = {row.row_id: row for row in ordered}
        train_rows = [by_id[row_id] for row_id in window.train_row_ids]
        validation_rows = [by_id[row_id] for row_id in window.validation_row_ids]
        baseline_class = _majority_class(train_rows)
        predictions = [
            prediction_from_majority_baseline(
                row.candidate_id,
                baseline_class=baseline_class,
                model_version=model_version,
                feature_schema_version=row.feature_schema_version,
            )
            for row in validation_rows
        ]
        predicted_classes = [baseline_class for _ in validation_rows]
        actual_classes = [str(row.outcome_class) for row in validation_rows]
        probabilities = [prediction.p_target_first for prediction in predictions]
        window_accuracy = accuracy(predicted_classes, actual_classes)
        window_brier = brier_score_target_first(probabilities, actual_classes)
        evaluated_windows.append(
            EvaluationWindow(
                window_id=window.window_id,
                train_row_ids=window.train_row_ids,
                validation_row_ids=window.validation_row_ids,
                metrics={
                    "accuracy": window_accuracy,
                    "brier_target_first": window_brier,
                },
            )
        )
        if window_accuracy is not None:
            accuracies.append(window_accuracy)
        if window_brier is not None:
            briers.append(window_brier)
        all_probabilities.extend(probabilities)
        all_actual.extend(actual_classes)

    aggregate_metrics = {
        "window_count": len(evaluated_windows),
        "mean_accuracy": sum(accuracies) / len(accuracies) if accuracies else None,
        "mean_brier_target_first": sum(briers) / len(briers) if briers else None,
    }
    calibration = {
        "ece_target_first": expected_calibration_error(
            all_probabilities,
            all_actual,
            bin_count=policy.calibration_bin_count,
        ),
        "bin_count": policy.calibration_bin_count,
    }
    placeholder_gate = {"promotion_allowed": False, "blocked_reasons": []}
    report = ModelEvaluationReport(
        report_id=_report_id(training_run_id, ordered, created_at, policy),
        report_version="model-evaluation-report-0.1.0",
        training_run_id=training_run_id,
        model_version=model_version,
        dataset_id=ordered[0].dataset_id if ordered else "UNKNOWN_DATASET",
        dataset_version=ordered[0].dataset_version if ordered else "UNKNOWN_DATASET_VERSION",
        created_at=created_at,
        evaluation_policy_version=policy.version,
        windows=evaluated_windows,
        aggregate_metrics=aggregate_metrics,
        calibration=calibration,
        promotion_gate=placeholder_gate,
        promotion_allowed=False,
    )
    from trading_system.evaluation.promotion import evaluate_promotion_gate

    return ModelEvaluationReport(
        report_id=report.report_id,
        report_version=report.report_version,
        training_run_id=report.training_run_id,
        model_version=report.model_version,
        dataset_id=report.dataset_id,
        dataset_version=report.dataset_version,
        created_at=report.created_at,
        evaluation_policy_version=report.evaluation_policy_version,
        windows=report.windows,
        aggregate_metrics=report.aggregate_metrics,
        calibration=report.calibration,
        promotion_gate=evaluate_promotion_gate(report, policy),
        promotion_allowed=False,
    )

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.contracts import ModelTrainingRun
from trading_system.models.readiness import TrainingPolicy, evaluate_training_readiness, included_rows

RUN_VERSION = "model-training-run-0.1.0"
MODEL_TYPE = "MAJORITY_CLASS_BASELINE"
MODEL_VERSION = "majority-class-baseline-0.1.0"


def _accuracy(rows: list[CandidateTrainingRow], baseline_class: str) -> float | None:
    if not rows:
        return None
    correct = sum(1 for row in rows if row.outcome_class == baseline_class)
    return correct / len(rows)


def _run_id(rows: list[CandidateTrainingRow], policy: TrainingPolicy, created_at: datetime, status: str) -> str:
    payload = {
        "rows": [row.row_id for row in rows],
        "policy": policy.version,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "status": status,
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def train_majority_baseline(
    rows: list[CandidateTrainingRow],
    policy: TrainingPolicy,
    *,
    created_at: datetime,
) -> ModelTrainingRun:
    readiness = evaluate_training_readiness(rows, policy)
    dataset_id = rows[0].dataset_id if rows else "UNKNOWN_DATASET"
    dataset_version = rows[0].dataset_version if rows else "UNKNOWN_DATASET_VERSION"
    feature_schema_version = rows[0].feature_schema_version if rows else "UNKNOWN_FEATURE_SCHEMA"
    label_version = next((row.label_version for row in rows if row.label_version), "UNKNOWN_LABEL_VERSION")

    if not readiness.ready:
        return ModelTrainingRun(
            run_id=_run_id(rows, policy, created_at, "BLOCKED"),
            run_version=RUN_VERSION,
            status="BLOCKED",
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            model_type=MODEL_TYPE,
            model_version=None,
            created_at=created_at,
            training_policy_version=policy.version,
            feature_schema_version=feature_schema_version,
            label_version=label_version,
            split_summary=readiness.split_summary,
            class_distribution=readiness.class_distribution,
            baseline_class=None,
            metrics={},
            blocked_reasons=readiness.blocked_reasons,
            promotion_allowed=False,
        )

    eligible = included_rows(rows)
    train_rows = [row for row in eligible if row.split == "TRAIN"]
    validation_rows = [row for row in eligible if row.split == "VALIDATION"]
    test_rows = [row for row in eligible if row.split == "TEST"]
    class_counts = Counter(row.outcome_class for row in train_rows)
    baseline_class = sorted(class_counts.items(), key=lambda item: (-item[1], str(item[0])))[0][0]
    metrics = {
        "validation_accuracy": _accuracy(validation_rows, baseline_class),
        "test_accuracy": _accuracy(test_rows, baseline_class),
    }
    return ModelTrainingRun(
        run_id=_run_id(rows, policy, created_at, "TRAINED"),
        run_version=RUN_VERSION,
        status="TRAINED",
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        model_type=MODEL_TYPE,
        model_version=MODEL_VERSION,
        created_at=created_at,
        training_policy_version=policy.version,
        feature_schema_version=feature_schema_version,
        label_version=label_version,
        split_summary=readiness.split_summary,
        class_distribution=readiness.class_distribution,
        baseline_class=str(baseline_class),
        metrics=metrics,
        blocked_reasons=(),
        promotion_allowed=False,
    )

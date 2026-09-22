from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

from trading_system.datasets.contracts import CandidateTrainingRow


@dataclass(frozen=True)
class TrainingPolicy:
    version: str
    min_train_rows: int
    min_validation_rows: int
    min_classes: int


@dataclass(frozen=True)
class TrainingReadinessResult:
    ready: bool
    blocked_reasons: tuple[str, ...]
    split_summary: dict[str, int]
    class_distribution: dict[str, int]


def load_training_policy(path: Path) -> TrainingPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TrainingPolicy(
        version=data["version"],
        min_train_rows=int(data["min_train_rows"]),
        min_validation_rows=int(data["min_validation_rows"]),
        min_classes=int(data["min_classes"]),
    )


def included_rows(rows: list[CandidateTrainingRow]) -> list[CandidateTrainingRow]:
    return [
        row
        for row in rows
        if row.included_in_training
        and row.outcome_class is not None
        and row.label_quality != "EXCLUDED_FROM_TRAINING"
    ]


def evaluate_training_readiness(
    rows: list[CandidateTrainingRow],
    policy: TrainingPolicy,
) -> TrainingReadinessResult:
    eligible = included_rows(rows)
    split_counts = Counter(row.split for row in eligible)
    class_counts = Counter(row.outcome_class for row in eligible if row.outcome_class is not None)
    split_summary = {
        "TRAIN": int(split_counts.get("TRAIN", 0)),
        "VALIDATION": int(split_counts.get("VALIDATION", 0)),
        "TEST": int(split_counts.get("TEST", 0)),
    }
    class_distribution = {str(key): int(value) for key, value in sorted(class_counts.items())}

    reasons: list[str] = []
    if split_summary["TRAIN"] < policy.min_train_rows:
        reasons.append("INSUFFICIENT_TRAIN_ROWS")
    if split_summary["VALIDATION"] < policy.min_validation_rows:
        reasons.append("MISSING_VALIDATION_ROWS")
    if len(class_distribution) < policy.min_classes:
        reasons.append("INSUFFICIENT_OUTCOME_CLASSES")

    return TrainingReadinessResult(
        ready=not reasons,
        blocked_reasons=tuple(reasons),
        split_summary=split_summary,
        class_distribution=class_distribution,
    )

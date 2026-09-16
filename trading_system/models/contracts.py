from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from trading_system.features.contracts import utc_iso


@dataclass(frozen=True)
class ModelTrainingRun:
    run_id: str
    run_version: str
    status: str
    dataset_id: str
    dataset_version: str
    model_type: str
    model_version: str | None
    created_at: datetime
    training_policy_version: str
    feature_schema_version: str
    label_version: str
    split_summary: Mapping[str, int]
    class_distribution: Mapping[str, int]
    baseline_class: str | None
    metrics: Mapping[str, float | int | None]
    blocked_reasons: tuple[str, ...]
    promotion_allowed: bool

    def to_payload(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_version": self.run_version,
            "status": self.status,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "created_at": utc_iso(self.created_at),
            "training_policy_version": self.training_policy_version,
            "feature_schema_version": self.feature_schema_version,
            "label_version": self.label_version,
            "split_summary": dict(sorted(self.split_summary.items())),
            "class_distribution": dict(sorted(self.class_distribution.items())),
            "baseline_class": self.baseline_class,
            "metrics": dict(sorted(self.metrics.items())),
            "blocked_reasons": list(self.blocked_reasons),
            "promotion_allowed": self.promotion_allowed,
        }

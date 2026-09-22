from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from trading_system.features.contracts import utc_iso


@dataclass(frozen=True)
class PredictionPayload:
    candidate_id: str
    model_id: str
    model_version: str
    feature_schema_version: str
    p_target_first: float
    p_stop_first: float
    p_expired: float
    expected_net_return_r: float
    expected_mae_r: float
    expected_mfe_r: float
    uncertainty: float
    coverage_status: str
    calibration_version: str

    def to_payload(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "feature_schema_version": self.feature_schema_version,
            "p_target_first": self.p_target_first,
            "p_stop_first": self.p_stop_first,
            "p_expired": self.p_expired,
            "expected_net_return_r": self.expected_net_return_r,
            "expected_mae_r": self.expected_mae_r,
            "expected_mfe_r": self.expected_mfe_r,
            "uncertainty": self.uncertainty,
            "coverage_status": self.coverage_status,
            "calibration_version": self.calibration_version,
        }


@dataclass(frozen=True)
class EvaluationWindow:
    window_id: str
    train_row_ids: tuple[str, ...]
    validation_row_ids: tuple[str, ...]
    metrics: Mapping[str, float | int | None]

    def to_payload(self) -> dict:
        return {
            "window_id": self.window_id,
            "train_row_ids": list(self.train_row_ids),
            "validation_row_ids": list(self.validation_row_ids),
            "metrics": dict(sorted(self.metrics.items())),
        }


@dataclass(frozen=True)
class ModelEvaluationReport:
    report_id: str
    report_version: str
    training_run_id: str
    model_version: str
    dataset_id: str
    dataset_version: str
    created_at: datetime
    evaluation_policy_version: str
    windows: list[EvaluationWindow]
    aggregate_metrics: Mapping[str, float | int | None]
    calibration: Mapping[str, float | int | None]
    promotion_gate: Mapping[str, object]
    promotion_allowed: bool

    def to_payload(self) -> dict:
        return {
            "report_id": self.report_id,
            "report_version": self.report_version,
            "training_run_id": self.training_run_id,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "created_at": utc_iso(self.created_at),
            "evaluation_policy_version": self.evaluation_policy_version,
            "windows": [window.to_payload() for window in self.windows],
            "aggregate_metrics": dict(sorted(self.aggregate_metrics.items())),
            "calibration": dict(sorted(self.calibration.items())),
            "promotion_gate": {
                "promotion_allowed": bool(self.promotion_gate["promotion_allowed"]),
                "blocked_reasons": list(self.promotion_gate["blocked_reasons"]),
            },
            "promotion_allowed": self.promotion_allowed,
        }

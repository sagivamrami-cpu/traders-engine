from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.evaluation.contracts import ModelEvaluationReport
from trading_system.features.contracts import utc_iso
from trading_system.models.contracts import ModelTrainingRun


@dataclass(frozen=True)
class ModelCard:
    card_id: str
    card_version: str
    model_type: str
    model_version: str
    dataset_id: str
    dataset_version: str
    training_run_id: str
    evaluation_report_id: str
    created_at: datetime
    approval_status: str
    approver: str | None
    promotion_allowed: bool
    blocked_reasons: tuple[str, ...]
    known_limitations: tuple[str, ...]
    rollback_target: str
    supported_scope: Mapping[str, tuple[str, ...]]

    def to_payload(self) -> dict:
        return {
            "card_id": self.card_id,
            "card_version": self.card_version,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "training_run_id": self.training_run_id,
            "evaluation_report_id": self.evaluation_report_id,
            "created_at": utc_iso(self.created_at),
            "approval_status": self.approval_status,
            "approver": self.approver,
            "promotion_allowed": self.promotion_allowed,
            "blocked_reasons": list(self.blocked_reasons),
            "known_limitations": list(self.known_limitations),
            "rollback_target": self.rollback_target,
            "supported_scope": {
                key: list(values) for key, values in sorted(self.supported_scope.items())
            },
        }


def _card_id(training_run: ModelTrainingRun, evaluation_report: ModelEvaluationReport, created_at: datetime) -> str:
    payload = {
        "training_run_id": training_run.run_id,
        "evaluation_report_id": evaluation_report.report_id,
        "model_version": training_run.model_version,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_model_card(
    training_run: ModelTrainingRun,
    evaluation_report: ModelEvaluationReport,
    *,
    created_at: datetime,
) -> ModelCard:
    blocked_reasons = tuple(evaluation_report.promotion_gate["blocked_reasons"])
    return ModelCard(
        card_id=_card_id(training_run, evaluation_report, created_at),
        card_version="model-card-0.1.0",
        model_type=training_run.model_type,
        model_version=training_run.model_version or "NO_MODEL_VERSION",
        dataset_id=training_run.dataset_id,
        dataset_version=training_run.dataset_version,
        training_run_id=training_run.run_id,
        evaluation_report_id=evaluation_report.report_id,
        created_at=created_at,
        approval_status="BLOCKED",
        approver=None,
        promotion_allowed=False,
        blocked_reasons=blocked_reasons,
        known_limitations=(
            "Fixture and synthetic examples are not production evidence.",
            "No live deployment is allowed from this card.",
            "No shadow, paper, or cost/fill evidence is attached.",
        ),
        rollback_target="NO_LIVE_MODEL",
        supported_scope={
            "symbols": ("TR_FIXTURE_SPY",),
            "timeframes": ("1m",),
            "graphs": ("tr-vshape-retest-long",),
            "environments": ("RESEARCH",),
        },
    )

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.csv_onboarding import build_raw_source_manifest_for_csv
from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.data_foundation.storage_policy import (
    RawDataRetentionDecision,
    evaluate_raw_data_retention,
    load_raw_data_retention_policy,
)
from trading_system.features.contracts import utc_iso
from trading_system.models.readiness import load_training_policy
from trading_system.research.offline_dry_run import build_local_csv_research_dry_run

VALIDATION_VERSION = "source-bundle-validation-0.1.0"
MODE = "LOCAL_SOURCE_BUNDLE_VALIDATION"
BLOCKED_ACTIONS = (
    "RAW_CSV_RETENTION",
    "PRODUCTION_VENDOR_APPROVAL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceBundleValidation:
    validation_id: str
    created_at: datetime
    status: str
    csv_path: Path
    metadata_path: Path
    retention_policy_path: Path
    raw_source_manifest: dict[str, Any]
    retention_decision: RawDataRetentionDecision
    dry_run_summary: dict[str, Any] | None
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "validation_version": VALIDATION_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": str(self.csv_path),
            "metadata_path": str(self.metadata_path),
            "retention_policy_path": str(self.retention_policy_path),
            "raw_source_manifest": self.raw_source_manifest,
            "retention_decision": self.retention_decision.to_payload(),
            "dry_run_summary": self.dry_run_summary,
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _validation_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _dry_run_summary(dry_run_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": dry_run_payload["run_id"],
        "training_status": dry_run_payload["training_run"]["status"],
        "promotion_allowed": dry_run_payload["training_run"]["promotion_allowed"],
        "safety_status": dry_run_payload["safety_status"],
    }


def validate_local_source_bundle(
    csv_path: Path,
    metadata_path: Path,
    retention_policy_path: Path,
    *,
    created_at: datetime,
) -> SourceBundleValidation:
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    normalization_policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    training_policy = load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml")
    retention_policy = load_raw_data_retention_policy(retention_policy_path)
    raw_manifest = build_raw_source_manifest_for_csv(
        csv_path,
        metadata,
        normalization_policy,
        symbol_map,
        ingested_at=created_at,
    )
    retention_decision = evaluate_raw_data_retention(retention_policy, raw_manifest)

    reasons: list[str] = []
    dry_summary = None
    if retention_decision.status != "MANIFEST_ONLY_ALLOWED":
        reasons.append("RETENTION_POLICY_BLOCKED")
        status = "BLOCKED"
    else:
        dry_run = build_local_csv_research_dry_run(
            csv_path,
            metadata,
            normalization_policy,
            symbol_map,
            training_policy,
            created_at=created_at,
        )
        dry_summary = _dry_run_summary(dry_run.to_payload())
        status = "ACCEPTED_FOR_DRY_RUN"

    id_payload = {
        "created_at": utc_iso(created_at),
        "csv_path": str(csv_path),
        "metadata_path": str(metadata_path),
        "retention_policy_path": str(retention_policy_path),
        "raw_file_sha256": raw_manifest["raw_file_sha256"],
        "retention_status": retention_decision.status,
        "dry_run_id": dry_summary["run_id"] if dry_summary else None,
        "status": status,
    }
    return SourceBundleValidation(
        validation_id=_validation_id(id_payload),
        created_at=created_at,
        status=status,
        csv_path=csv_path,
        metadata_path=metadata_path,
        retention_policy_path=retention_policy_path,
        raw_source_manifest=raw_manifest,
        retention_decision=retention_decision,
        dry_run_summary=dry_summary,
        blocked_reasons=tuple(reasons),
    )

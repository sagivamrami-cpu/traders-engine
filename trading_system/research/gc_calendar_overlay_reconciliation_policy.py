from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data, validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
POLICY_VERSION = "gc-calendar-overlay-reconciliation-policy-0.1.0"
MODE = "GC_CALENDAR_OVERLAY_RECONCILIATION_POLICY"
SCHEMA_PATH = ROOT / "schemas/gc_calendar_overlay_reconciliation_policy.schema.json"


@dataclass(frozen=True)
class GcCalendarOverlayReconciliationPolicyReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected overlay reconciliation policy YAML mapping")
    return to_plain_data(loaded)


def build_gc_calendar_overlay_reconciliation_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcCalendarOverlayReconciliationPolicyReport:
    policy = _load_yaml(policy_path)
    payload = {
        "policy_id": _id({"created_at": utc_iso(created_at), "policy": policy}),
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "calendar_id": str(policy["calendar_id"]),
        "status": str(policy["status"]),
        "source_strategy_ref": str(policy["source_strategy_ref"]),
        "construction_policy_ref": str(policy["construction_policy_ref"]),
        "cme_evidence_manifest_ref": str(policy["cme_evidence_manifest_ref"]),
        "observed_full_aggregate_status_ref": str(policy["observed_full_aggregate_status_ref"]),
        "observed_gap_profile_status_ref": str(policy["observed_gap_profile_status_ref"]),
        "session_calendar_gate_status": str(policy["session_calendar_gate_status"]),
        "observed_gap_profile_status": str(policy["observed_gap_profile_status"]),
        "overlay_table_status": str(policy["overlay_table_status"]),
        "reconciliation_table_status": str(policy["reconciliation_table_status"]),
        "required_overlay_types": list(policy["required_overlay_types"]),
        "required_reconciliation_controls": list(policy["required_reconciliation_controls"]),
        "calendar_registration_allowed": bool(policy["calendar_registration_allowed"]),
        "dataset_construction_allowed": bool(policy["dataset_construction_allowed"]),
        "resampling_allowed": bool(policy["resampling_allowed"]),
        "training_allowed": bool(policy["training_allowed"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": list(policy["blocked_reasons"]),
    }
    return GcCalendarOverlayReconciliationPolicyReport(payload=payload)

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
POLICY_VERSION = "gc-session-calendar-construction-policy-0.1.0"
MODE = "GC_SESSION_CALENDAR_CONSTRUCTION_POLICY"
SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_construction_policy.schema.json"


@dataclass(frozen=True)
class GcSessionCalendarConstructionPolicyReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected construction policy YAML mapping")
    return to_plain_data(loaded)


def build_gc_session_calendar_construction_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcSessionCalendarConstructionPolicyReport:
    policy = _load_yaml(policy_path)
    payload = {
        "report_id": _id({"created_at": utc_iso(created_at), "policy": policy}),
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "calendar_id": str(policy["calendar_id"]),
        "status": str(policy["status"]),
        "source_strategy_ref": str(policy["source_strategy_ref"]),
        "source_strategy_decision_ref": str(policy["source_strategy_decision_ref"]),
        "implementation_decision_ref": str(policy["implementation_decision_ref"]),
        "databento_status_skip_decision_ref": str(policy["databento_status_skip_decision_ref"]),
        "scope_amendment_decision_ref": str(policy["scope_amendment_decision_ref"]),
        "registered_calendar_ref": str(policy["registered_calendar_ref"]),
        "session_calendar_gate_status": str(policy["session_calendar_gate_status"]),
        "calendar_registration_allowed": bool(policy["calendar_registration_allowed"]),
        "construction_allowed": bool(policy["construction_allowed"]),
        "normal_session_template": dict(policy["normal_session_template"]),
        "era_versioning": dict(policy["era_versioning"]),
        "overlay_requirements": list(policy["overlay_requirements"]),
        "reconciliation_requirements": list(policy["reconciliation_requirements"]),
        "bar_membership_rules": dict(policy["bar_membership_rules"]),
        "required_next_evidence": list(policy["required_next_evidence"]),
        "dataset_construction_allowed": bool(policy["dataset_construction_allowed"]),
        "resampling_allowed": bool(policy["resampling_allowed"]),
        "training_allowed": bool(policy["training_allowed"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": list(policy["blocked_reasons"]),
    }
    return GcSessionCalendarConstructionPolicyReport(payload=payload)

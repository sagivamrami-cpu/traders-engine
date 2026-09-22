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

POLICY_VERSION = "gc-bar-session-timestamp-policy-0.1.0"
MODE = "GC_BAR_SESSION_TIMESTAMP_POLICY"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_bar_session_timestamp_policy.schema.json"


@dataclass(frozen=True)
class GcBarSessionTimestampPolicyReport:
    report_id: str
    created_at: datetime
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def load_gc_bar_session_timestamp_policy(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected GC bar/session/timestamp policy mapping")
    policy = to_plain_data(loaded)
    validation_body = _build_payload_body(policy, created_at="1970-01-01T00:00:00Z")
    validate_json_payload(SCHEMA_PATH, {"report_id": "0" * 64, **validation_body})
    return policy


def _blocked_reasons(policy: dict[str, Any]) -> list[str]:
    gate_reasons = {
        "BAR_BOUNDARY": "BAR_BOUNDARY_GATE_UNSATISFIED",
        "SESSION_CALENDAR": "SESSION_CALENDAR_GATE_UNSATISFIED",
        "TIMESTAMP_ROLE": "TIMESTAMP_ROLE_GATE_UNSATISFIED",
        "AVAILABLE_AT_POLICY": "AVAILABLE_AT_POLICY_GATE_UNSATISFIED",
        "MISSING_BAR_POLICY": "MISSING_BAR_POLICY_GATE_UNSATISFIED",
        "DATASET_CONSTRUCTION_AUTHORIZATION": "DATASET_CONSTRUCTION_AUTHORIZATION_GATE_UNSATISFIED",
    }
    reasons = [
        gate_reasons[gate]
        for gate in policy["required_remaining_gates"]
        if gate in gate_reasons
    ]
    if policy["session_calendar_policy"]["holiday_overlay_status"] == "REQUIRED_NOT_ENCODED":
        reasons.append("HOLIDAY_OVERLAY_REQUIRED_NOT_ENCODED")
    if policy["timestamp_policy"]["status"] == "PENDING_HUMAN_CONFIRMATION_AND_VENDOR_EVIDENCE":
        reasons.append("VENDOR_TIMESTAMP_EVIDENCE_PENDING")
    if policy["session_calendar_policy"]["utc_bar_session_membership_status"] == "REQUIRED_NOT_ENCODED":
        reasons.append("UTC_BAR_SESSION_MEMBERSHIP_REQUIRED_NOT_ENCODED")
    return list(dict.fromkeys(reasons))


def _build_payload_body(policy: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    # Construction/resampling flags are honoured only when no gate remains; training
    # is never enabled by this policy.
    gates_closed = not list(policy["required_remaining_gates"])
    return {
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": created_at,
        "status": str(policy["status"]),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "candidate_timeframe": str(policy["candidate_timeframe"]),
        "bar_boundary_policy": policy["bar_boundary_policy"],
        "session_calendar_policy": policy["session_calendar_policy"],
        "timestamp_policy": policy["timestamp_policy"],
        "dataset_construction_allowed": gates_closed and policy.get("dataset_construction_allowed") is True,
        "resampling_allowed": gates_closed and policy.get("resampling_allowed") is True,
        "training_allowed": False,
        "required_remaining_gates": list(policy["required_remaining_gates"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": _blocked_reasons(policy),
    }


def build_gc_bar_session_timestamp_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcBarSessionTimestampPolicyReport:
    policy = load_gc_bar_session_timestamp_policy(policy_path)
    body = _build_payload_body(policy, created_at=utc_iso(created_at))
    report_id = _report_id(body)
    payload = {"report_id": report_id, **body}
    return GcBarSessionTimestampPolicyReport(
        report_id=report_id,
        created_at=created_at,
        payload=payload,
    )

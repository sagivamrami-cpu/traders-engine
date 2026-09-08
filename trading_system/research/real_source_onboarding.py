from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.features.contracts import utc_iso
from trading_system.research.intake_packet import REDACTED_LOCAL_PATH, build_real_ohlcv_intake_packet
from trading_system.research.readiness import (
    APPROVED_DECISION,
    DEFERRED_DECISION,
    RealDataDecisionFile,
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)

PREFLIGHT_VERSION = "real-source-onboarding-preflight-0.1.0"
MODE = "REAL_SOURCE_ONBOARDING_PREFLIGHT"
RECORDS_PRESENT_STATUS = "PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED"
BLOCKED_ACTIONS = (
    "BUILD_PRODUCTION_TRAINING_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
APPROVED_REQUIRED_ITEMS = frozenset(
    {
        "REAL_HISTORICAL_OHLCV_CSV",
        "PRODUCTION_OHLCV_VENDOR_DECISION",
        "FIRST_REAL_SYMBOL",
        "FIRST_HISTORICAL_INTERVAL",
        "RAW_DATA_STORAGE_LICENSE_APPROVAL",
    }
)
DECIDED_REQUIRED_ITEMS = APPROVED_REQUIRED_ITEMS | frozenset(
    {"ORDER_FLOW_SOURCE_DECISION", "OPTIONS_SOURCE_DECISION"}
)
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RealSourceOnboardingPreflight:
    preflight_id: str
    created_at: datetime
    status: str
    decisions_path_present: bool
    intake_packet: dict[str, Any]
    readiness: dict[str, Any]
    source_identity: dict[str, Any]
    allowed_next_actions: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "preflight_id": self.preflight_id,
            "preflight_version": PREFLIGHT_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": REDACTED_LOCAL_PATH,
            "metadata_path": REDACTED_LOCAL_PATH,
            "decisions_path": REDACTED_LOCAL_PATH if self.decisions_path_present else None,
            "intake_packet": self.intake_packet,
            "readiness": self.readiness,
            "source_identity": self.source_identity,
            "production_allowed": False,
            "allowed_next_actions": list(self.allowed_next_actions),
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _preflight_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _load_decisions(decisions_path: Path | None, reasons: list[str]) -> RealDataDecisionFile | None:
    if decisions_path is None:
        reasons.append("MISSING_DECISIONS_FILE")
        return None
    try:
        return load_real_data_decisions(decisions_path)
    except Exception:
        reasons.append("INVALID_DECISIONS_FILE")
        return None


def _preflight_decision_reasons(decisions: RealDataDecisionFile | None) -> tuple[str, ...]:
    if decisions is None:
        return ()
    by_item = {decision.item_id: decision.decision for decision in decisions.decisions}
    reasons: list[str] = []
    for item_id in sorted(APPROVED_REQUIRED_ITEMS):
        if by_item.get(item_id) != APPROVED_DECISION:
            reasons.append(f"{item_id}_NOT_APPROVED")
    for item_id in sorted(DECIDED_REQUIRED_ITEMS - APPROVED_REQUIRED_ITEMS):
        if by_item.get(item_id) not in (APPROVED_DECISION, DEFERRED_DECISION):
            reasons.append(f"{item_id}_NOT_DECIDED")
    for item_id in sorted(set(by_item) - DECIDED_REQUIRED_ITEMS):
        reasons.append(f"UNKNOWN_PREFLIGHT_DECISION_{item_id}")
    return tuple(reasons)


def _readiness_payload(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["required_items"] = [_redact_readiness_item(item) for item in payload["required_items"]]
    enriched["production_allowed"] = False
    id_payload = {key: value for key, value in enriched.items() if key != "report_id"}
    enriched["report_id"] = _preflight_id(id_payload)
    return enriched


def _redact_readiness_item(item: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(item)
    decision = redacted.get("decision")
    if isinstance(decision, dict):
        redacted["decision"] = {
            "decision": decision.get("decision"),
            "approver": "HUMAN_DECISION_APPROVER_REDACTED",
            "decided_at": decision.get("decided_at"),
            "scope": "HUMAN_DECISION_SCOPE_REDACTED",
            "evidence": [
                "HUMAN_DECISION_EVIDENCE_REDACTED"
                for _ in decision.get("evidence", [])
            ],
        }
    return redacted


def build_real_source_onboarding_preflight(
    csv_path: Path,
    metadata_path: Path,
    decisions_path: Path | None,
    *,
    created_at: datetime,
    project_root: Path | None = None,
) -> RealSourceOnboardingPreflight:
    root = ROOT if project_root is None else project_root
    reasons: list[str] = []
    intake = build_real_ohlcv_intake_packet(
        csv_path,
        metadata_path,
        created_at=created_at,
        project_root=root,
    ).to_payload()
    decisions = _load_decisions(decisions_path, reasons)
    checklist = load_real_data_readiness_checklist(root / "configs/research/real-data-readiness-checklist.yaml")
    readiness = _readiness_payload(
        build_real_data_readiness_report(
            checklist,
            created_at=created_at,
            decisions=decisions,
        ).to_payload()
    )

    source_identity = intake["source_identity"]
    if intake["status"] != "BLOCKED_NEEDS_HUMAN_DECISION":
        reasons.append("INTAKE_PACKET_NOT_READY_FOR_REAL_SOURCE_ONBOARDING")
    if source_identity["status"] != "REAL_SOURCE_PENDING_HUMAN_DECISION":
        reasons.append("SOURCE_IDENTITY_NOT_PENDING_REAL_SOURCE")
    reasons.extend(_preflight_decision_reasons(decisions))
    blocked_reasons = _unique([*reasons, *readiness["blocked_reasons"]])

    status = "BLOCKED"
    allowed_next_actions: tuple[str, ...] = ()
    if not reasons and set(readiness["blocked_reasons"]).issubset(
        {"MISSING_ORDER_FLOW_SOURCE_DECISION", "MISSING_OPTIONS_SOURCE_DECISION"}
    ):
        status = RECORDS_PRESENT_STATUS

    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "intake_packet_id": intake["packet_id"],
        "readiness_report_id": readiness["report_id"],
        "source_identity": source_identity,
        "allowed_next_actions": allowed_next_actions,
        "blocked_reasons": blocked_reasons,
    }
    return RealSourceOnboardingPreflight(
        preflight_id=_preflight_id(id_payload),
        created_at=created_at,
        status=status,
        decisions_path_present=decisions_path is not None,
        intake_packet=intake,
        readiness=readiness,
        source_identity=source_identity,
        allowed_next_actions=allowed_next_actions,
        blocked_reasons=blocked_reasons,
    )

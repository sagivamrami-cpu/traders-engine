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

POLICY_VERSION = "gc-label-split-policy-0.1.0"
MODE = "GC_LABEL_SPLIT_POLICY"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_label_split_policy.schema.json"


@dataclass(frozen=True)
class GcLabelSplitPolicyReport:
    report_id: str
    created_at: datetime
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _blocked_reasons(policy: dict[str, Any]) -> list[str]:
    reasons = []
    if "LABEL_CONTRACT" in policy["required_remaining_gates"]:
        reasons.append("LABEL_CONTRACT_GATE_UNSATISFIED")
    if "SPLIT_AND_EMBARGO_POLICY" in policy["required_remaining_gates"]:
        reasons.append("SPLIT_AND_EMBARGO_POLICY_GATE_UNSATISFIED")
    if policy["label_contract_policy"]["d7_decision_status"] == "NEEDS_HUMAN_DECISION_RECORD":
        reasons.append("D7_DECISION_RECORD_MISSING")
    if policy["split_and_embargo_policy"]["d8_decision_status"] == "NEEDS_HUMAN_DECISION_RECORD":
        reasons.append("D8_DECISION_RECORD_MISSING")
    if policy["label_contract_policy"]["target_stop_threshold_status"].startswith("UNSPECIFIED"):
        reasons.append("TARGET_STOP_THRESHOLDS_UNSPECIFIED")
    if policy["label_contract_policy"]["horizon_status"].startswith("UNSPECIFIED"):
        reasons.append("MAX_LABEL_HORIZON_UNSPECIFIED")
    if policy["split_and_embargo_policy"]["embargo_size_status"] == "PENDING_MAX_LABEL_HORIZON":
        reasons.append("EMBARGO_SIZE_UNSPECIFIED")
    if policy["split_and_embargo_policy"]["row_level_2017_mask_status"] == "REQUIRED_NOT_IMPLEMENTED":
        reasons.append("ROW_LEVEL_2017_MASK_NOT_IMPLEMENTED")
    if policy["label_contract_policy"]["fill_truth_status"].startswith("UNSPECIFIED"):
        reasons.append("CONTRACT_IDENTITY_AND_FILL_TRUTH_UNSATISFIED")
    upstream_gates = {
        "BAR_BOUNDARY",
        "SESSION_CALENDAR",
        "TIMESTAMP_ROLE",
        "AVAILABLE_AT_POLICY",
        "ROLL_POLICY",
        "CONTRACT_IDENTITY",
        "GRAPH_TRADE_CONTRACT",
        "COST_FILL_POLICY",
        "MISSING_BAR_POLICY",
        "DATASET_IDENTITY",
        "CANONICAL_OHLCV_INPUT",
        "CANONICAL_ORDER_FLOW_INPUT",
        "ORDER_FLOW_SOURCE_DECISION",
        "ORDER_FLOW_ERA_MAP",
        "ROW_LEVEL_2017_MASK",
        "CUMULATIVE_FEATURE_POLICY",
        "DATASET_CONSTRUCTION_AUTHORIZATION",
    }
    if upstream_gates.intersection(policy["required_remaining_gates"]):
        reasons.append("UPSTREAM_DATASET_GATES_UNSATISFIED")
    return list(dict.fromkeys(reasons))


def _build_payload_body(policy: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    gates_closed = not list(policy["required_remaining_gates"])
    return {
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": created_at,
        "status": str(policy["status"]),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "candidate_timeframe": str(policy["candidate_timeframe"]),
        "label_contract_policy": policy["label_contract_policy"],
        "split_and_embargo_policy": policy["split_and_embargo_policy"],
        # Honoured only when no upstream gate remains; training is never enabled here.
        "dataset_construction_allowed": gates_closed and policy.get("dataset_construction_allowed") is True,
        "label_building_allowed": gates_closed and policy.get("label_building_allowed") is True,
        "split_building_allowed": gates_closed and policy.get("split_building_allowed") is True,
        "training_allowed": False,
        "required_remaining_gates": list(policy["required_remaining_gates"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": _blocked_reasons(policy),
    }


def load_gc_label_split_policy(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected GC label/split policy mapping")
    policy = to_plain_data(loaded)
    validation_body = _build_payload_body(policy, created_at="1970-01-01T00:00:00Z")
    validate_json_payload(SCHEMA_PATH, {"report_id": "0" * 64, **validation_body})
    return policy


def build_gc_label_split_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcLabelSplitPolicyReport:
    policy = load_gc_label_split_policy(policy_path)
    body = _build_payload_body(policy, created_at=utc_iso(created_at))
    report_id = _report_id(body)
    payload = {"report_id": report_id, **body}
    return GcLabelSplitPolicyReport(
        report_id=report_id,
        created_at=created_at,
        payload=payload,
    )

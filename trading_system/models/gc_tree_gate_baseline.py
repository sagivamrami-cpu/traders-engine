from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_tree_gate_baseline_audit.schema.json"
AUDIT_VERSION = "gc-tree-gate-baseline-audit-0.1.0"
POLICY_VERSION = "gc-conservative-tree-gate-baseline-0.1.0"
MODE = "GC_TREE_GATE_BASELINE_AUDIT"
TREE_STAGES = [
    "DATA",
    "POSITION",
    "SESSION",
    "LOCATION",
    "CYCLE",
    "CONTEXT",
    "PATTERN",
    "VECTOR",
    "TRAP",
    "RETEST",
    "TARGET_RISK",
    "TRIGGER",
    "SCALE_IN",
    "INVALIDATION",
]
IMPLEMENTED_STAGES = {"DATA", "SESSION", "CONTEXT", "TARGET_RISK"}
BLOCKED_ACTIONS = [
    "TRAIN_ADDITIONAL_FLAT_MODEL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcTreeGateBaselineAudit:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _audit_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "audit_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _gate_catalog() -> list[dict[str, Any]]:
    return [
        {
            "stage_order": index,
            "stage": stage,
            "gate_source": "IMPLEMENTED_FROM_EXISTING_ROW" if stage in IMPLEMENTED_STAGES else "MISSING_TYPED_TREE_GATE",
            "missing_policy": "EVALUATE" if stage in IMPLEMENTED_STAGES else "UNKNOWN_THEN_WAIT",
        }
        for index, stage in enumerate(TREE_STAGES, start=1)
    ]


def _required_feature_status(row: CandidateTrainingRow, features: Sequence[str]) -> tuple[str, str]:
    missing = [name for name in features if _numeric(row.features.get(name)) is None]
    if missing:
        return "UNKNOWN", f"missing flat source features: {','.join(missing)}"
    return "PASS", "required flat source features are present"


def _data_gate(row: CandidateTrainingRow) -> tuple[str, str]:
    reasons = []
    if row.candidate_status != "ELIGIBLE":
        reasons.append(f"candidate_status={row.candidate_status}")
    if not row.included_in_training:
        reasons.append("included_in_training=false")
    if row.label_quality != "HIGH":
        reasons.append(f"label_quality={row.label_quality}")
    if row.outcome_class is None:
        reasons.append("outcome_class_missing")
    if reasons:
        return "BLOCK", ";".join(reasons)
    return "PASS", "eligible high-quality row with outcome label"


def _known_gate(row: CandidateTrainingRow, stage: str) -> tuple[str, str]:
    if stage == "DATA":
        return _data_gate(row)
    if stage == "SESSION":
        if row.observation_time is None:
            return "UNKNOWN", "observation_time_missing"
        return "PASS", "timestamp is present; detailed session phase gate is still pending"
    if stage == "CONTEXT":
        return _required_feature_status(row, ("ret_1", "ret_4", "ret_8", "ret_14", "range_over_atr"))
    if stage == "TARGET_RISK":
        if row.contract_version is None or _numeric(row.outcome_return_r) is None:
            return "UNKNOWN", "trade contract or R outcome is missing"
        return "PASS", "trade contract and R outcome are present"
    return "UNKNOWN", "typed tree gate is not implemented yet"


def _trace(row: CandidateTrainingRow) -> dict[str, Any]:
    gate_path = []
    blocked = False
    for index, stage in enumerate(TREE_STAGES, start=1):
        if blocked:
            status, reason = "NOT_EVALUATED", "previous hard gate blocked the candidate"
        else:
            status, reason = _known_gate(row, stage)
            blocked = status == "BLOCK"
        gate_path.append({"stage_order": index, "stage": stage, "status": status, "reason": reason})
    final_action = "NO_TRADE" if any(gate["status"] == "BLOCK" for gate in gate_path) else "WAIT"
    return {
        "candidate_id": row.candidate_id,
        "observation_time": utc_iso(row.observation_time),
        "direction": row.direction,
        "final_action": final_action,
        "gate_path": gate_path,
    }


def _empty_status_counts() -> dict[str, int]:
    return {"PASS": 0, "BLOCK": 0, "UNKNOWN": 0, "NOT_EVALUATED": 0}


def _stage_summary(traces: Sequence[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {stage: _empty_status_counts() for stage in TREE_STAGES}
    for trace in traces:
        for gate in trace["gate_path"]:
            summary[gate["stage"]][gate["status"]] += 1
    return summary


def _reason_counts(traces: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for trace in traces:
        for gate in trace["gate_path"]:
            if gate["status"] in {"BLOCK", "UNKNOWN"}:
                counter[f"{gate['stage']}:{gate['reason']}"] += 1
    return [{"reason": reason, "count": count} for reason, count in counter.most_common(20)]


def _action_counts(traces: Sequence[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(trace["final_action"] for trace in traces)
    return {action: int(counter.get(action, 0)) for action in ("LONG", "SHORT", "WAIT", "NO_TRADE")}


def _sample_traces(traces: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    waits = [trace for trace in traces if trace["final_action"] == "WAIT"][:10]
    no_trades = [trace for trace in traces if trace["final_action"] == "NO_TRADE"][:10]
    sample = waits + no_trades
    if sample:
        return sample[:20]
    return list(traces[:20])


def build_gc_tree_gate_baseline_audit(
    rows: Sequence[CandidateTrainingRow],
    tree_gap_review: dict[str, Any],
    *,
    created_at: datetime,
) -> GcTreeGateBaselineAudit:
    ordered = sorted(rows, key=lambda row: row.observation_time)
    traces = [_trace(row) for row in ordered]
    payload = {
        "audit_id": "",
        "audit_version": AUDIT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "TREE_GATE_BASELINE_AUDIT_READY",
        "dataset_id": str(tree_gap_review["dataset_id"]),
        "variant": str(tree_gap_review.get("variant", "order_flow")),
        "source_tree_gap_review_id": str(tree_gap_review["review_id"]),
        "baseline_policy_version": POLICY_VERSION,
        "gate_catalog": _gate_catalog(),
        "aggregate_counts": {
            "rows_evaluated": len(traces),
            "final_actions": _action_counts(traces),
        },
        "stage_summary": _stage_summary(traces),
        "top_rejection_reasons": _reason_counts(traces),
        "sample_traces": _sample_traces(traces),
        "required_next_artifacts": [
            "typed_gate_schema_per_stage",
            "manual_tree_rule_parameters",
            "candidate_rejection_reason_catalog",
            "stage_level_replay_annotation",
            "long_short_gate_policy",
            "regime_gate_policy",
        ],
        "additional_model_training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_58_TYPED_TREE_GATE_IMPLEMENTATION",
    }
    payload["audit_id"] = _audit_id(payload)
    return GcTreeGateBaselineAudit(payload)

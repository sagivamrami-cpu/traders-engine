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
from trading_system.research import gc_real_dataset_builder as builder

ROOT = Path(__file__).resolve().parents[2]
POLICY_VERSION = "gc-missing-bar-policy-0.1.0"
MODE = "GC_MISSING_BAR_POLICY"
SCHEMA_PATH = ROOT / "schemas/gc_missing_bar_policy.schema.json"


@dataclass(frozen=True)
class GcMissingBarPolicyReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def load_gc_missing_bar_policy(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected GC missing-bar policy mapping")
    return to_plain_data(loaded)


def builder_constant_mismatches(policy: dict[str, Any]) -> list[str]:
    """The policy file must describe exactly what the builder implements."""
    mismatches: list[str] = []
    checks = (
        ("builder_version", builder.BUILDER_VERSION),
        ("feature_lookback_bars", builder.FEATURE_LOOKBACK_BARS),
        ("label_horizon_bars", builder.HORIZON_BARS),
        ("calendar_id", builder.CALENDAR_ID),
        ("missing_bar_reason", builder.REASON_OHLCV_MISSING_BAR),
    )
    for key, expected in checks:
        if policy.get(key) != expected:
            mismatches.append(f"{key.upper()}_MISMATCH")
    if list(policy.get("exclusion_reasons_all_variants", [])) != list(builder.ALL_VARIANT_REASONS):
        mismatches.append("ALL_VARIANT_REASONS_MISMATCH")
    if list(policy.get("exclusion_reasons_order_flow_variant", [])) != list(builder.ORDER_FLOW_VARIANT_REASONS):
        mismatches.append("ORDER_FLOW_VARIANT_REASONS_MISMATCH")
    return mismatches


def build_gc_missing_bar_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcMissingBarPolicyReport:
    policy = load_gc_missing_bar_policy(policy_path)
    mismatches = builder_constant_mismatches(policy)
    blocked_reasons = [*mismatches]
    if policy.get("dataset_construction_allowed") is not False:
        blocked_reasons.append("DATASET_CONSTRUCTION_MUST_REMAIN_BLOCKED_IN_POLICY")
    if policy.get("training_allowed") is not False:
        blocked_reasons.append("TRAINING_MUST_REMAIN_BLOCKED_IN_POLICY")
    body = {
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "candidate_timeframe": str(policy["candidate_timeframe"]),
        "status": str(policy["status"]),
        "missing_bar_policy_gate_status": str(policy["missing_bar_policy_gate_status"]),
        "policy_decision_refs": list(policy["policy_decision_refs"]),
        "calendar_scope_decision_ref": str(policy["calendar_scope_decision_ref"]),
        "calendar_id": str(policy["calendar_id"]),
        "calendar_ref": str(policy["calendar_ref"]),
        "implementation_module": str(policy["implementation_module"]),
        "builder_version": str(policy["builder_version"]),
        "fill_policy": str(policy["fill_policy"]),
        "session_membership_rule": str(policy["session_membership_rule"]),
        "straddle_policy": str(policy["straddle_policy"]),
        "out_of_session_data_policy": str(policy["out_of_session_data_policy"]),
        "expected_grid_rule": str(policy["expected_grid_rule"]),
        "missing_bar_rule": str(policy["missing_bar_rule"]),
        "feature_lookback_bars": int(policy["feature_lookback_bars"]),
        "label_horizon_bars": int(policy["label_horizon_bars"]),
        "family_status": dict(policy["family_status"]),
        "order_flow_gap_rule": str(policy["order_flow_gap_rule"]),
        "order_flow_coverage_rule": str(policy["order_flow_coverage_rule"]),
        "order_flow_optional_variant_allowed": bool(policy["order_flow_optional_variant_allowed"]),
        "exclusion_reasons_all_variants": list(policy["exclusion_reasons_all_variants"]),
        "exclusion_reasons_order_flow_variant": list(policy["exclusion_reasons_order_flow_variant"]),
        "missing_bar_reason": str(policy["missing_bar_reason"]),
        "manifest_requirements": list(policy["manifest_requirements"]),
        "holiday_special_hours_overlay_status": str(policy["holiday_special_hours_overlay_status"]),
        "overlay_reconciliation_table_status": str(policy["overlay_reconciliation_table_status"]),
        "session_calendar_gate_status": str(policy["session_calendar_gate_status"]),
        "builder_constants_match": not mismatches,
        "dataset_construction_allowed": bool(policy["dataset_construction_allowed"]),
        "training_allowed": bool(policy["training_allowed"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": blocked_reasons,
    }
    payload = {"report_id": _id(body), **body}
    return GcMissingBarPolicyReport(payload=payload)

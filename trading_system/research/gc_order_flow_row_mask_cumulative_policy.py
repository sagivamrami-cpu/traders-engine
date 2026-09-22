from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data, validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
POLICY_VERSION = "gc-order-flow-row-mask-cumulative-policy-0.1.0"
MODE = "GC_ORDER_FLOW_ROW_MASK_CUMULATIVE_POLICY"
SCHEMA_PATH = ROOT / "schemas/gc_order_flow_row_mask_cumulative_policy.schema.json"
DAMAGED_START = pd.Timestamp("2017-01-01T00:00:00Z")
DAMAGED_END = pd.Timestamp("2017-06-01T00:00:00Z")


@dataclass(frozen=True)
class GcOrderFlowRowMaskCumulativePolicyReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected GC order-flow row-mask cumulative policy mapping")
    return to_plain_data(loaded)


def _coerce_utc_minutes(minutes: pd.Series) -> pd.Series:
    values = pd.Series(pd.to_datetime(minutes), index=minutes.index)
    timezone = getattr(values.dt, "tz", None)
    if timezone is None:
        return values.dt.tz_localize("UTC")
    return values.dt.tz_convert("UTC")


def apply_gc_order_flow_training_mask(minutes: pd.Series) -> pd.Series:
    utc_minutes = _coerce_utc_minutes(minutes)
    return (utc_minutes < DAMAGED_START) | (utc_minutes >= DAMAGED_END)


def build_gc_order_flow_row_mask_cumulative_policy_report(
    policy_path: Path,
    *,
    created_at: datetime,
) -> GcOrderFlowRowMaskCumulativePolicyReport:
    policy = _load_yaml(policy_path)
    body = {
        "policy_version": POLICY_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(policy["canonical_symbol"]),
        "status": str(policy["status"]),
        "canonical_order_flow_input_ref": str(policy["canonical_order_flow_input_ref"]),
        "selected_member": str(policy["selected_member"]),
        "timestamp_column": str(policy["timestamp_column"]),
        "timestamp_policy": str(policy["timestamp_policy"]),
        "mask_predicate": str(policy["mask_predicate"]),
        "known_damaged_aggressor_window": dict(policy["known_damaged_aggressor_window"]),
        "order_flow_era_map_gate_status": str(policy["order_flow_era_map_gate_status"]),
        "cumulative_feature_policy_status": str(policy["cumulative_feature_policy_status"]),
        "archived_cvd_policy": str(policy["archived_cvd_policy"]),
        "allowed_order_flow_feature_columns": list(policy["allowed_order_flow_feature_columns"]),
        "forbidden_order_flow_feature_columns": list(policy["forbidden_order_flow_feature_columns"]),
        "order_flow_source_decision_status": str(policy["order_flow_source_decision_status"]),
        "dataset_construction_allowed": bool(policy["dataset_construction_allowed"]),
        "training_allowed": bool(policy["training_allowed"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "blocked_reasons": list(policy["blocked_reasons"]),
    }
    payload = {"report_id": _id(body), **body}
    return GcOrderFlowRowMaskCumulativePolicyReport(payload=payload)

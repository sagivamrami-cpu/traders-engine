from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research.gc_order_flow_era_map import (
    build_gc_order_flow_era_map,
)

REPORT_VERSION = "gc-order-flow-availability-era-policy-0.1.0"
MODE = "GC_ORDER_FLOW_AVAILABILITY_ERA_POLICY"
SOURCE_BLOCKED_STATUS = "FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_order_flow_availability_era_policy.schema.json"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
BLOCKED_ACTIONS = (
    "BUILD_REAL_DATASET",
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_CVD_FEATURES",
    "USE_ARCHIVED_CVD_COLUMN",
    "INGEST_PRECOMPUTED_CVD",
    "BUILD_MACRO_FEATURES",
    "QUERY_OPTIONS_DATA",
    "INGEST_ORDERFLOW_4H_CSV",
    "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
    "MAP_GC_TO_XAUUSD",
    "MAP_GC_TO_GLD",
    "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
    "TRAIN_PRODUCTION_MODEL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
REQUIRED_REMAINING_GATES = (
    "ORDER_FLOW_ERA_MAP",
    "ORDER_FLOW_SOURCE_DECISION",
    "CANONICAL_ORDER_FLOW_INPUT",
    "CANONICAL_OHLCV_INPUT",
    "ROW_LEVEL_2017_MASK",
    "CUMULATIVE_FEATURE_POLICY",
    "DATASET_CONSTRUCTION_AUTHORIZATION",
)


@dataclass(frozen=True)
class GcOrderFlowAvailabilityEraPolicy:
    report_id: str
    created_at: datetime
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _parse_utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value).tz_convert("UTC")


def _iso(value: pd.Timestamp) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _regime(
    regime_id: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    inclusion_status: str,
) -> dict[str, str]:
    return {
        "regime_id": regime_id,
        "semantics": "HALF_OPEN_UTC_ANNOTATION_ONLY_NOT_ROW_MASK",
        "start": _iso(start),
        "end": _iso(end),
        "inclusion_status": inclusion_status,
        "row_level_mask_status": "REQUIRED_NOT_IMPLEMENTED",
        "cumulative_carry_status": "RESET_REQUIRED",
    }


def _split_regimes(role: str, start: str | None, end: str | None, damaged: dict[str, str]) -> list[dict[str, str]]:
    if start is None or end is None:
        return []
    file_start = _parse_utc(start)
    file_end = _parse_utc(end)
    if role == "OHLCV_1M":
        return [
            _regime(
                "OHLCV_NOT_SUBJECT_TO_AGGRESSOR_DAMAGE_WITHOUT_SEPARATE_DECISION",
                file_start,
                file_end,
                "OHLCV_NOT_SUBJECT_TO_AGGRESSOR_DAMAGE_WITHOUT_SEPARATE_DECISION",
            )
        ]
    if role != "ORDER_FLOW_1M":
        return [
            _regime(
                "NO_KNOWN_DAMAGE_OVERLAP",
                file_start,
                file_end,
                "CANDIDATE_ONLY_REQUIRES_SOURCE_AND_CANONICAL_INPUT_DECISION",
            )
        ]
    damaged_start = _parse_utc(damaged["start"])
    damaged_end = _parse_utc(damaged["end"])

    regimes: list[dict[str, str]] = []
    if file_start < damaged_start:
        regimes.append(
            _regime(
                "PRE_KNOWN_DAMAGE_UNVERIFIED",
                file_start,
                min(file_end, damaged_start),
                "CANDIDATE_ONLY_REQUIRES_ROW_LEVEL_MASK",
            )
        )
    if file_start < damaged_end and damaged_start <= file_end:
        regimes.append(
            _regime(
                "KNOWN_DAMAGED_AGGRESSOR_WINDOW",
                max(file_start, damaged_start),
                min(file_end, damaged_end),
                "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
            )
        )
    if file_end >= damaged_end:
        regimes.append(
            _regime(
                "POST_KNOWN_DAMAGE_REQUIRES_PIT_RECOMPUTE",
                max(file_start, damaged_end),
                file_end,
                "CANDIDATE_ONLY_REQUIRES_SOURCE_AND_CANONICAL_INPUT_DECISION",
            )
        )
    if not regimes:
        regimes.append(
            _regime(
                "NO_KNOWN_DAMAGE_OVERLAP",
                file_start,
                file_end,
                "CANDIDATE_ONLY_REQUIRES_SOURCE_AND_CANONICAL_INPUT_DECISION",
            )
        )
    return regimes


def build_gc_order_flow_availability_era_policy(
    zip_path: Path,
    gates_path: Path,
    decisions_path: Path,
    *,
    created_at: datetime,
) -> GcOrderFlowAvailabilityEraPolicy:
    catalog = build_gc_order_flow_era_map(
        zip_path,
        gates_path,
        decisions_path,
        created_at=created_at,
    ).to_payload()
    blocked_reasons = list(catalog["blocked_reasons"])
    per_file_policies = [
        {
            "file": era["file"],
            "role": era["role"],
            "identity_status": era["identity_status"],
            "timestamp_column": era["timestamp_column"],
            "timezone_status": era["timezone_status"],
            "range_start": era["start"],
            "range_end": era["end"],
            "cvd_present": era["cvd_present"],
            "cumulative_column_status": era["cumulative_column_status"],
            "allowed_for_training": False,
            "regimes": _split_regimes(
                era["role"],
                era["start"],
                era["end"],
                catalog["known_damaged_aggressor_window"],
            ),
        }
        for era in catalog["parquet_eras"]
    ]
    if any(not policy["regimes"] for policy in per_file_policies):
        blocked_reasons.append("FILE_RANGE_UNRESOLVED")
    status = SOURCE_BLOCKED_STATUS if not blocked_reasons and per_file_policies else "BLOCKED"
    body = {
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": status,
        "policy_applies_to": "UNSELECTED_ZIP_MEMBERS",
        "zip_path": REDACTED_LOCAL_PATH,
        "zip_sha256": catalog["zip_sha256"],
        "canonical_symbol": "GC",
        "source_id": "databento-gc-order-flow",
        "policy_scope": "PARQUET_FILE_RANGE_REGIME_POLICY_ONLY",
        "order_flow_era_map_gate_status": "UNSATISFIED_POLICY_CANDIDATE_ONLY",
        "known_damaged_aggressor_window": catalog["known_damaged_aggressor_window"],
        "per_file_policies": per_file_policies,
        "cumulative_boundary_policy": {
            "status": "BLOCKED_PENDING_IMPLEMENTATION",
            "reset_required_at": [
                "FILE_START",
                "KNOWN_DAMAGED_WINDOW_START",
                "KNOWN_DAMAGED_WINDOW_END",
                "WALK_FORWARD_FOLD_BOUNDARY",
            ],
            "forbidden_carry_features": ["CVD", "CUMULATIVE_DELTA"],
            "archived_cvd_use": "FORBIDDEN",
        },
        "dataset_construction_allowed": False,
        "training_allowed": False,
        "allowed_next_actions": [],
        "blocked_actions": list(BLOCKED_ACTIONS),
        "required_remaining_gates": list(REQUIRED_REMAINING_GATES),
        "blocked_reasons": blocked_reasons,
    }
    report_id = _report_id(body)
    payload = {"report_id": report_id, **body}
    return GcOrderFlowAvailabilityEraPolicy(report_id=report_id, created_at=created_at, payload=payload)

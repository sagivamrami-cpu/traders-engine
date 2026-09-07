from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml

from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research.readiness import load_real_data_decisions

REPORT_VERSION = "gc-order-flow-era-map-0.1.0"
MODE = "GC_ORDER_FLOW_ERA_MAP"
READY_STATUS = "ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_order_flow_era_map.schema.json"
BLOCKED_ACTIONS = (
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_REAL_DATASET",
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
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
SOURCE_READINESS_BLOCKERS = (
    "ORDER_FLOW_SOURCE_DECISION_OPEN",
    "ORDER_FLOW_ERA_MAP_UNSATISFIED_FULL_AVAILABILITY_POLICY",
    "CANONICAL_ORDER_FLOW_INPUT_UNDECLARED",
    "CANONICAL_OHLCV_INPUT_UNDECLARED",
    "CUMULATIVE_FEATURE_POLICY_BLOCKED",
    "ROW_LEVEL_2017_MASK_UNIMPLEMENTED",
)


@dataclass(frozen=True)
class GcOrderFlowEraMap:
    report_id: str
    created_at: datetime
    status: str
    zip_sha256: str | None
    known_damaged_aggressor_window: dict[str, str]
    parquet_eras: tuple[dict[str, Any], ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "report_id": self.report_id,
            "report_version": REPORT_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "zip_path": REDACTED_LOCAL_PATH,
            "zip_sha256": self.zip_sha256,
            "canonical_symbol": "GC",
            "source_id": "databento-gc-order-flow",
            "interval_semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
            "order_flow_era_map_gate_status": "UNSATISFIED_FILE_CATALOG_ONLY",
            "cumulative_feature_policy_status": "BLOCKED_PENDING_PIT_FOLD_LOCAL_ERA_GAP_POLICY",
            "raw_tick_eras": "UNPROFILED_NAME_ONLY",
            "known_damaged_aggressor_window": self.known_damaged_aggressor_window,
            "parquet_eras": list(self.parquet_eras),
            "order_flow_source_decision_status": "OPEN_HUMAN_DECISION",
            "dataset_construction_allowed": False,
            "training_allowed": False,
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "source_readiness_blockers": list(SOURCE_READINESS_BLOCKERS),
            "blocked_reasons": list(self.blocked_reasons),
        }
        validate_json_payload(SCHEMA_PATH, payload)
        return payload


def _unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _classify_role(name: str) -> str:
    lower = name.lower()
    if "_of_1m.parquet" in lower:
        return "ORDER_FLOW_1M"
    if "ohlcv" in lower and lower.endswith(".parquet"):
        return "OHLCV_1M"
    return "UNKNOWN_PARQUET"


def _classify_timezone(values: pd.Series) -> str:
    if not pd.api.types.is_datetime64_any_dtype(values):
        return "UNKNOWN"
    timezone = getattr(values.dt, "tz", None)
    if timezone is None:
        return "NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE"
    if str(timezone) == "UTC":
        return "UTC"
    return "UNKNOWN"


def _iso_from_timestamp(value: Any, timezone_status: str) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        if timezone_status != "NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE":
            return None
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value).tz_convert("UTC")


def _half_open_overlap(
    start: str | None,
    end: str | None,
    damaged: dict[str, str],
) -> bool:
    if start is None or end is None:
        return False
    era_start = _parse_utc(start)
    era_end = _parse_utc(end)
    damaged_start = _parse_utc(damaged["start"])
    damaged_end = _parse_utc(damaged["end"])
    return era_start < damaged_end and damaged_start <= era_end


def _parquet_era(name: str, data: bytes, damaged: dict[str, str]) -> dict[str, Any]:
    parquet = pq.ParquetFile(io.BytesIO(data))
    columns = list(parquet.schema_arrow.names)
    row_count = parquet.metadata.num_rows
    timestamp_column = "minute" if "minute" in columns else columns[-1] if columns else None
    timezone_status = "UNKNOWN"
    start: str | None = None
    end: str | None = None
    if timestamp_column is not None and row_count > 0:
        table = parquet.read(columns=[timestamp_column])
        values = table.to_pandas(ignore_metadata=True)[timestamp_column]
        timezone_status = _classify_timezone(values)
        start = _iso_from_timestamp(values.iloc[0], timezone_status)
        end = _iso_from_timestamp(values.iloc[-1], timezone_status)
    return {
        "file": name,
        "role": _classify_role(name),
        "columns": columns,
        "timestamp_column": timestamp_column,
        "timezone_status": timezone_status,
        "identity_status": "UNDECLARED_SESSION_OR_IDENTITY_VARIANT",
        "row_count": row_count,
        "start": start,
        "end": end,
        "cvd_present": "cvd" in {column.lower() for column in columns},
        "cumulative_column_status": (
            "PRECOMPUTED_CUMULATIVE_UNSAFE"
            if "cvd" in {column.lower() for column in columns}
            else "NOT_PRESENT"
        ),
        "file_range_overlaps_known_damage": _half_open_overlap(start, end, damaged),
    }


def _load_damaged_window(gates_path: Path) -> dict[str, str]:
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    if not isinstance(gates, dict):
        raise ValueError("order-flow gates must be a mapping")
    damaged = gates.get("known_damaged_aggressor_window")
    if not isinstance(damaged, dict):
        raise ValueError("order-flow gates require known_damaged_aggressor_window")
    return {
        "start": str(damaged["start"]),
        "end": str(damaged["end"]),
        "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
        "status": str(damaged["status"]),
    }


def _decision_reasons(decisions_path: Path) -> list[str]:
    decisions = load_real_data_decisions(decisions_path)
    by_item = {decision.item_id: decision.decision for decision in decisions.decisions}
    if by_item.get("ORDER_FLOW_SOURCE_DECISION") not in (None, "APPROVED"):
        return ["ORDER_FLOW_SOURCE_DECISION_MUST_REMAIN_OPEN_FOR_ERA_MAP_PROFILE"]
    return []


def build_gc_order_flow_era_map(
    zip_path: Path,
    gates_path: Path,
    decisions_path: Path,
    *,
    created_at: datetime,
) -> GcOrderFlowEraMap:
    reasons: list[str] = []
    zip_sha256: str | None = None
    parquet_eras: tuple[dict[str, Any], ...] = ()
    try:
        damaged = _load_damaged_window(gates_path)
    except Exception:
        damaged = {
            "start": "2017-01-01T00:00:00Z",
            "end": "2017-06-01T00:00:00Z",
            "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
            "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
        }
        reasons.append("INVALID_ORDER_FLOW_GATES")
    try:
        reasons.extend(_decision_reasons(decisions_path))
    except Exception:
        reasons.append("INVALID_DECISIONS_FILE")
    try:
        zip_sha256 = sha256_file(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            parquet_names = sorted(name for name in archive.namelist() if name.lower().endswith(".parquet"))
            parquet_eras = tuple(_parquet_era(name, archive.read(name), damaged) for name in parquet_names)
    except (OSError, zipfile.BadZipFile):
        reasons.append("UNREADABLE_ORDER_FLOW_ZIP")
    except Exception:
        reasons.append("ORDER_FLOW_ERA_MAP_PREPARATION_FAILED")

    if not parquet_eras:
        reasons.append("PARQUET_FILES_MISSING")
    if not any(era["role"] == "ORDER_FLOW_1M" for era in parquet_eras):
        reasons.append("ORDER_FLOW_PARQUET_FILES_MISSING")

    blocked_reasons = _unique(reasons)
    status = READY_STATUS if not blocked_reasons else "BLOCKED"
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "zip_sha256": zip_sha256,
        "parquet_files": [era["file"] for era in parquet_eras],
        "blocked_reasons": list(blocked_reasons),
    }
    return GcOrderFlowEraMap(
        report_id=_report_id(id_payload),
        created_at=created_at,
        status=status,
        zip_sha256=zip_sha256,
        known_damaged_aggressor_window=damaged,
        parquet_eras=parquet_eras,
        blocked_reasons=blocked_reasons,
    )

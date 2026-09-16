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
from trading_system.research.readiness import DEFERRED_DECISION, load_real_data_decisions

PROFILE_VERSION = "databento-gc-order-flow-profile-0.1.0"
MODE = "DATABENTO_GC_ORDER_FLOW_ZIP_PROFILE"
READY_STATUS = "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/databento_gc_order_flow_profile.schema.json"
BLOCKED_ACTIONS = (
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_REAL_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "USE_ARCHIVED_CVD_COLUMN",
    "INGEST_PRECOMPUTED_CVD",
    "INGEST_ORDERFLOW_4H_CSV",
    "JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS",
    "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
    "QUERY_OPTIONS_DATA",
    "JOIN_MACRO_FEATURES",
    "USE_REVISED_MACRO_SERIES",
    "MAP_GC_TO_XAUUSD",
    "MAP_GC_TO_GLD",
    "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
SOURCE_READINESS_BLOCKERS = (
    "ORDER_FLOW_SOURCE_DECISION_OPEN",
    "CONTRACT_IDENTITY_UNDECLARED",
    "ERA_MAP_UNMEASURED",
    "PRECOMPUTED_CVD_COLUMN_UNSAFE",
)


@dataclass(frozen=True)
class DatabentoGcOrderFlowProfile:
    profile_id: str
    created_at: datetime
    status: str
    zip_sha256: str | None
    readme_present: bool
    source_id: str
    vendor: str
    dataset: str
    raw_symbol: str
    parquet_files: tuple[str, ...]
    dbn_zst_files: tuple[str, ...]
    sampled_parquet_count: int
    one_minute_order_flow_files: tuple[str, ...]
    one_minute_ohlcv_files: tuple[str, ...]
    raw_tick_files: tuple[str, ...]
    columns_by_file: dict[str, list[str]]
    timestamp_column_by_file: dict[str, str | None]
    timezone_by_file: dict[str, str]
    row_count_by_file: dict[str, int]
    range_by_file: dict[str, dict[str, str | None]]
    known_damaged_aggressor_window: dict[str, str]
    cumulative_feature_policy_status: str
    contract_identity_status: str
    raw_tick_schema_family: str
    cumulative_column_status_by_file: dict[str, str]
    parquet_file_identity_status_by_file: dict[str, str]
    reference_4h_csv_status: str
    timeframe_status: str
    first_baseline_candidate: str
    macro_feature_status: str
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_version": PROFILE_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "zip_path": REDACTED_LOCAL_PATH,
            "zip_sha256": self.zip_sha256,
            "readme_present": self.readme_present,
            "source_id": self.source_id,
            "vendor": self.vendor,
            "dataset": self.dataset,
            "canonical_symbol": "GC",
            "raw_symbol": self.raw_symbol,
            "order_flow_source_decision_status": "OPEN_HUMAN_DECISION",
            "options_source_decision_status": "DEFERRED_TO_V2_DO_NOT_QUERY",
            "parquet_files": list(self.parquet_files),
            "dbn_zst_files": list(self.dbn_zst_files),
            "sampled_parquet_count": self.sampled_parquet_count,
            "parquet_entry_count": len(self.parquet_files),
            "dbn_zst_entry_count": len(self.dbn_zst_files),
            "one_minute_order_flow_files": list(self.one_minute_order_flow_files),
            "one_minute_ohlcv_files": list(self.one_minute_ohlcv_files),
            "raw_tick_files": list(self.raw_tick_files),
            "columns_by_file": self.columns_by_file,
            "timestamp_column_by_file": self.timestamp_column_by_file,
            "timezone_by_file": self.timezone_by_file,
            "row_count_by_file": self.row_count_by_file,
            "range_by_file": self.range_by_file,
            "known_damaged_aggressor_window": self.known_damaged_aggressor_window,
            "cumulative_feature_policy_status": self.cumulative_feature_policy_status,
            "contract_identity_status": self.contract_identity_status,
            "raw_tick_schema_family": self.raw_tick_schema_family,
            "cumulative_column_status_by_file": self.cumulative_column_status_by_file,
            "parquet_file_identity_status_by_file": self.parquet_file_identity_status_by_file,
            "reference_4h_csv_status": self.reference_4h_csv_status,
            "timeframe_status": self.timeframe_status,
            "first_baseline_candidate": self.first_baseline_candidate,
            "macro_feature_status": self.macro_feature_status,
            "production_allowed": False,
            "dataset_construction_allowed": False,
            "training_allowed": False,
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "source_readiness_blockers": list(SOURCE_READINESS_BLOCKERS),
            "blocked_reasons": list(self.blocked_reasons),
        }
        validate_json_payload(SCHEMA_PATH, payload)
        return payload


def _profile_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _unique_reasons(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected YAML mapping")
    return loaded


def _classify_timezone(values: pd.Series) -> str:
    if not pd.api.types.is_datetime64_any_dtype(values):
        return "UNKNOWN"
    tz = getattr(values.dt, "tz", None)
    if tz is None:
        return "NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE"
    if str(tz) == "UTC":
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


def _parquet_profile(data: bytes) -> tuple[list[str], int, str | None, str, str | None, str | None]:
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
    return columns, row_count, timestamp_column, timezone_status, start, end


def _select_samples(entries: list[str], max_sample_entries: int) -> list[str]:
    if not entries or max_sample_entries <= 0:
        return []
    candidates = [entries[0], entries[len(entries) // 2], entries[-1], *entries]
    return list(dict.fromkeys(candidates))[:max_sample_entries]


def _metadata_reasons(metadata: dict[str, Any]) -> list[str]:
    expected = {
        "source_id": "databento-gc-order-flow",
        "source_status": "PROFILE_ONLY_NOT_SOURCE_APPROVED",
        "vendor": "DATABENTO",
        "dataset": "GLBX.MDP3",
        "canonical_symbol": "GC",
        "raw_symbol": "GC",
        "allowed_use": "PROFILE_ONLY",
    }
    return [
        "INVALID_ORDER_FLOW_METADATA"
        for key, value in expected.items()
        if str(metadata.get(key, "")).strip() != value
    ][:1]


def _readiness_reasons(decisions_path: Path) -> list[str]:
    try:
        decisions = load_real_data_decisions(decisions_path)
    except Exception:
        return ["INVALID_DECISIONS_FILE"]
    by_item = {decision.item_id: decision.decision for decision in decisions.decisions}
    reasons: list[str] = []
    if by_item.get("ORDER_FLOW_SOURCE_DECISION") not in (None, "APPROVED"):
        reasons.append("ORDER_FLOW_SOURCE_DECISION_MUST_REMAIN_OPEN_FOR_PROFILE")
    if by_item.get("OPTIONS_SOURCE_DECISION") != DEFERRED_DECISION:
        reasons.append("OPTIONS_SOURCE_DECISION_MUST_BE_DEFERRED")
    return reasons


def build_databento_gc_order_flow_profile(
    zip_path: Path,
    metadata_path: Path,
    gates_path: Path,
    decisions_path: Path,
    *,
    created_at: datetime,
    max_sample_entries: int = 5,
) -> DatabentoGcOrderFlowProfile:
    reasons: list[str] = []
    metadata: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    try:
        metadata = _load_yaml(metadata_path)
        reasons.extend(_metadata_reasons(metadata))
    except Exception:
        reasons.append("INVALID_ORDER_FLOW_METADATA")
    try:
        gates = _load_yaml(gates_path)
    except Exception:
        reasons.append("INVALID_ORDER_FLOW_GATES")
    reasons.extend(_readiness_reasons(decisions_path))

    zip_sha256: str | None = None
    readme_present = False
    parquet_files: tuple[str, ...] = ()
    dbn_zst_files: tuple[str, ...] = ()
    one_minute_order_flow_files: tuple[str, ...] = ()
    one_minute_ohlcv_files: tuple[str, ...] = ()
    raw_tick_files: tuple[str, ...] = ()
    columns_by_file: dict[str, list[str]] = {}
    timestamp_column_by_file: dict[str, str | None] = {}
    timezone_by_file: dict[str, str] = {}
    row_count_by_file: dict[str, int] = {}
    range_by_file: dict[str, dict[str, str | None]] = {}
    cumulative_column_status_by_file: dict[str, str] = {}
    parquet_file_identity_status_by_file: dict[str, str] = {}

    try:
        zip_sha256 = sha256_file(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            names = sorted(archive.namelist())
            readme_present = any(name.lower().endswith("readme.md") for name in names)
            parquet_files = tuple(name for name in names if name.lower().endswith(".parquet"))
            dbn_zst_files = tuple(name for name in names if name.lower().endswith(".dbn.zst"))
            one_minute_order_flow_files = tuple(
                name for name in parquet_files if "_of_1m.parquet" in name
            )
            one_minute_ohlcv_files = tuple(
                name for name in parquet_files if "ohlcv" in name.lower()
            )
            raw_tick_files = dbn_zst_files
            for name in _select_samples(list(parquet_files), max_sample_entries):
                columns, row_count, timestamp_column, timezone_status, start, end = _parquet_profile(
                    archive.read(name)
                )
                columns_by_file[name] = columns
                timestamp_column_by_file[name] = timestamp_column
                timezone_by_file[name] = timezone_status
                row_count_by_file[name] = row_count
                range_by_file[name] = {"start": start, "end": end}
                cumulative_column_status_by_file[name] = (
                    "PRECOMPUTED_CUMULATIVE_UNSAFE"
                    if "cvd" in {column.lower() for column in columns}
                    else "NOT_PRESENT"
                )
                parquet_file_identity_status_by_file[name] = "UNDECLARED_SESSION_OR_IDENTITY_VARIANT"
    except (OSError, zipfile.BadZipFile):
        reasons.append("UNREADABLE_ORDER_FLOW_ZIP")
    except Exception:
        reasons.append("ORDER_FLOW_PROFILE_PREPARATION_FAILED")

    if not readme_present:
        reasons.append("README_MISSING")
    if not one_minute_order_flow_files:
        reasons.append("ORDER_FLOW_PARQUET_FILES_MISSING")
    if not raw_tick_files:
        reasons.append("RAW_TICK_FILES_MISSING")

    damaged = gates.get("known_damaged_aggressor_window", {}) if isinstance(gates, dict) else {}
    cumulative = gates.get("cumulative_features", {}) if isinstance(gates, dict) else {}
    reference = gates.get("reference_4h_csv", {}) if isinstance(gates, dict) else {}
    timeframe = gates.get("timeframe", {}) if isinstance(gates, dict) else {}
    macro = gates.get("macro_features", {}) if isinstance(gates, dict) else {}
    blocked_reasons = _unique_reasons(reasons)
    status = READY_STATUS if not blocked_reasons else "BLOCKED"
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "zip_sha256": zip_sha256,
        "parquet_entry_count": len(parquet_files),
        "dbn_zst_entry_count": len(dbn_zst_files),
        "blocked_reasons": list(blocked_reasons),
    }
    return DatabentoGcOrderFlowProfile(
        profile_id=_profile_id(id_payload),
        created_at=created_at,
        status=status,
        zip_sha256=zip_sha256,
        readme_present=readme_present,
        source_id=str(metadata.get("source_id", "databento-gc-order-flow")),
        vendor=str(metadata.get("vendor", "DATABENTO")),
        dataset=str(metadata.get("dataset", "GLBX.MDP3")),
        raw_symbol=str(metadata.get("raw_symbol", "GC")),
        parquet_files=parquet_files,
        dbn_zst_files=dbn_zst_files,
        sampled_parquet_count=len(columns_by_file),
        one_minute_order_flow_files=one_minute_order_flow_files,
        one_minute_ohlcv_files=one_minute_ohlcv_files,
        raw_tick_files=raw_tick_files,
        columns_by_file=columns_by_file,
        timestamp_column_by_file=timestamp_column_by_file,
        timezone_by_file=timezone_by_file,
        row_count_by_file=row_count_by_file,
        range_by_file=range_by_file,
        known_damaged_aggressor_window={
            "status": str(damaged.get("status", "EXCLUDE_FROM_ORDER_FLOW_FEATURES")),
            "start": str(damaged.get("start", "2017-01-01T00:00:00Z")),
            "end": str(damaged.get("end", "2017-06-01T00:00:00Z")),
            "reason": str(damaged.get("reason", "DAMAGED_AGGRESSOR_SIDE_DELTA")),
        },
        cumulative_feature_policy_status=str(
            cumulative.get("status", "BLOCKED_PENDING_PIT_ERA_GAP_POLICY")
        ),
        contract_identity_status=str(
            metadata.get("contract_identity_status", "UNDECLARED_PENDING_HUMAN_DECISION")
        ),
        raw_tick_schema_family="UNPROFILED_NAME_ONLY",
        cumulative_column_status_by_file=cumulative_column_status_by_file,
        parquet_file_identity_status_by_file=parquet_file_identity_status_by_file,
        reference_4h_csv_status=str(reference.get("status", "REFERENCE_ONLY_DO_NOT_INGEST")),
        timeframe_status=str(timeframe.get("status", "RESEARCH_PARAMETER_PENDING")),
        first_baseline_candidate=str(timeframe.get("first_baseline_candidate", "30m")),
        macro_feature_status=str(
            macro.get("status", "REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE")
        ),
        blocked_reasons=blocked_reasons,
    )

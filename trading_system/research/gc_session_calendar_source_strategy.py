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

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
STRATEGY_VERSION = "gc-session-calendar-source-strategy-0.1.0"
STRATEGY_MODE = "GC_SESSION_CALENDAR_SOURCE_STRATEGY"
OBSERVED_PROFILE_VERSION = "gc-observed-activity-calendar-profile-0.1.0"
OBSERVED_MODE = "GC_OBSERVED_ACTIVITY_CALENDAR_PROFILE"
FULL_AGGREGATE_VERSION = "gc-observed-activity-full-aggregate-0.1.0"
FULL_AGGREGATE_MODE = "GC_OBSERVED_ACTIVITY_FULL_AGGREGATE"
STRATEGY_SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_source_strategy.schema.json"
OBSERVED_SCHEMA_PATH = ROOT / "schemas/gc_observed_activity_calendar_profile.schema.json"
FULL_AGGREGATE_SCHEMA_PATH = ROOT / "schemas/gc_observed_activity_full_aggregate.schema.json"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
SOURCE_STRATEGY_REF = "configs/data/gc-session-calendar-source-strategy.yaml"
BLOCKED_ACTIONS = (
    "REGISTER_SESSION_CALENDAR",
    "QUERY_DATABENTO_STATUS_SCHEMA",
    "RESAMPLE_REAL_BARS",
    "BUILD_REAL_DATASET",
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_REAL_LABELS",
    "TRAIN_PRODUCTION_MODEL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
OBSERVED_BLOCKED_ACTIONS = (
    "REGISTER_SESSION_CALENDAR",
    "RESAMPLE_REAL_BARS",
    "BUILD_REAL_DATASET",
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_REAL_LABELS",
    "TRAIN_PRODUCTION_MODEL",
)
OBSERVED_BLOCKED_REASONS = (
    "OBSERVED_ACTIVITY_NOT_CALENDAR_AUTHORITY",
    "SESSION_CALENDAR_GATE_UNSATISFIED",
    "ERA_VERSIONED_OVERLAY_NOT_IMPLEMENTED",
)


@dataclass(frozen=True)
class GcSessionCalendarSourceStrategyReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(STRATEGY_SCHEMA_PATH, self.payload)
        return self.payload


@dataclass(frozen=True)
class GcObservedActivityCalendarProfile:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(OBSERVED_SCHEMA_PATH, self.payload)
        return self.payload


@dataclass(frozen=True)
class GcObservedActivityFullAggregate:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(FULL_AGGREGATE_SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("YAML payload must be an object")
    return data


def _utc_z(value: pd.Timestamp) -> str:
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    else:
        value = value.tz_convert("UTC")
    return value.isoformat().replace("+00:00", "Z")


def _sample_names(entries: list[str], max_sample_entries: int) -> list[str]:
    if max_sample_entries <= 0 or len(entries) <= max_sample_entries:
        return entries
    candidates = [entries[0], entries[len(entries) // 2], entries[-1]]
    return list(dict.fromkeys(candidates))[:max_sample_entries]


def build_gc_session_calendar_source_strategy_report(
    strategy_path: Path,
    *,
    created_at: datetime,
) -> GcSessionCalendarSourceStrategyReport:
    strategy = _load_yaml(strategy_path)
    payload = {
        "report_id": _id(
            {
                "created_at": utc_iso(created_at),
                "strategy": strategy,
            }
        ),
        "strategy_version": STRATEGY_VERSION,
        "mode": STRATEGY_MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(strategy["canonical_symbol"]),
        "calendar_id": str(strategy["calendar_id"]),
        "status": str(strategy["status"]),
        "decision_ref": str(strategy["decision_ref"]),
        "session_calendar_gate_status": str(strategy["session_calendar_gate_status"]),
        "calendar_registration_allowed": bool(strategy["calendar_registration_allowed"]),
        "observed_activity_leg": dict(strategy["observed_activity_leg"]),
        "cme_official_leg": dict(strategy["cme_official_leg"]),
        "databento_status_leg": dict(strategy["databento_status_leg"]),
        "tradingview_leg": dict(strategy["tradingview_leg"]),
        "era_versioning": dict(strategy["era_versioning"]),
        "scheduled_vs_observed_policy": str(strategy["scheduled_vs_observed_policy"]),
        "disagreement_policy": str(strategy["disagreement_policy"]),
        "dataset_construction_allowed": bool(strategy["dataset_construction_allowed"]),
        "resampling_allowed": bool(strategy["resampling_allowed"]),
        "training_allowed": bool(strategy["training_allowed"]),
        "blocked_actions": list(strategy["blocked_actions"]),
        "blocked_reasons": list(strategy["blocked_reasons"]),
    }
    return GcSessionCalendarSourceStrategyReport(payload=payload)


def build_gc_observed_activity_calendar_profile(
    zip_path: Path,
    strategy_path: Path,
    *,
    created_at: datetime,
    max_sample_entries: int = 3,
) -> GcObservedActivityCalendarProfile:
    strategy = build_gc_session_calendar_source_strategy_report(
        strategy_path,
        created_at=created_at,
    ).to_payload()
    if strategy["calendar_registration_allowed"] is not False:
        raise ValueError("strategy must not allow calendar registration")

    sampled_periods: list[dict[str, Any]] = []
    sampled_timestamps: list[pd.Timestamp] = []
    row_count = 0
    with zipfile.ZipFile(zip_path) as archive:
        entries = sorted(name for name in archive.namelist() if name.lower().endswith(".parquet"))
        if not entries:
            raise ValueError("no parquet entries found")
        for name in entries:
            parquet_file = pq.ParquetFile(io.BytesIO(archive.read(name)))
            row_count += parquet_file.metadata.num_rows
        for name in _sample_names(entries, max_sample_entries):
            frame = pd.read_parquet(io.BytesIO(archive.read(name)), engine="pyarrow")
            if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.name != "ts_event":
                raise ValueError("observed activity profile requires ts_event DatetimeIndex")
            if frame.index.tz is None:
                raise ValueError("observed activity profile requires UTC-aware ts_event")
            ordered_index = frame.index.sort_values()
            first = ordered_index.min()
            last = ordered_index.max()
            sampled_timestamps.extend(pd.Timestamp(value) for value in ordered_index)
            sampled_periods.append(
                {
                    "member": name,
                    "row_count": int(len(frame)),
                    "first_observed_at": _utc_z(first),
                    "last_observed_at": _utc_z(last),
                }
            )

    ordered_sample = sorted(sampled_timestamps)
    gaps = [
        int((right - left).total_seconds())
        for left, right in zip(ordered_sample, ordered_sample[1:])
    ]
    largest_gap = max(gaps) if gaps else 0
    payload = {
        "profile_id": _id(
            {
                "created_at": utc_iso(created_at),
                "row_count": row_count,
                "sampled_periods": sampled_periods,
                "largest_sampled_gap_seconds": largest_gap,
            }
        ),
        "profile_version": OBSERVED_PROFILE_VERSION,
        "mode": OBSERVED_MODE,
        "created_at": utc_iso(created_at),
        "status": "OBSERVED_ACTIVITY_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED",
        "canonical_symbol": "GC",
        "local_path": REDACTED_LOCAL_PATH,
        "source_strategy_ref": SOURCE_STRATEGY_REF,
        "observed_activity_leg_status": "PROFILE_ONLY_ZERO_COST_EVIDENCE_LEG",
        "parquet_entry_count": len(entries),
        "sampled_entry_count": len(sampled_periods),
        "row_count": int(row_count),
        "first_observed_at": _utc_z(min(ordered_sample)),
        "last_observed_at": _utc_z(max(ordered_sample)),
        "largest_sampled_gap_seconds": int(largest_gap),
        "sampled_periods": sampled_periods,
        "session_calendar_gate_status": "UNSATISFIED_OBSERVED_ACTIVITY_ONLY",
        "calendar_registration_allowed": False,
        "dataset_construction_allowed": False,
        "resampling_allowed": False,
        "training_allowed": False,
        "blocked_actions": list(OBSERVED_BLOCKED_ACTIONS),
        "blocked_reasons": list(OBSERVED_BLOCKED_REASONS),
    }
    return GcObservedActivityCalendarProfile(payload=payload)


def _ts_event_stats(parquet_file: pq.ParquetFile) -> tuple[pd.Timestamp, pd.Timestamp]:
    minimum: pd.Timestamp | None = None
    maximum: pd.Timestamp | None = None
    for row_group_index in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(row_group_index)
        for column_index in range(row_group.num_columns):
            column = row_group.column(column_index)
            if column.path_in_schema != "ts_event":
                continue
            stats = column.statistics
            if stats is None or stats.min is None or stats.max is None:
                raise ValueError("full observed activity aggregate requires ts_event parquet statistics")
            current_min = pd.Timestamp(stats.min)
            current_max = pd.Timestamp(stats.max)
            minimum = current_min if minimum is None else min(minimum, current_min)
            maximum = current_max if maximum is None else max(maximum, current_max)
    if minimum is None or maximum is None:
        raise ValueError("full observed activity aggregate requires ts_event metadata")
    return minimum, maximum


def build_gc_observed_activity_full_aggregate(
    zip_path: Path,
    strategy_path: Path,
    *,
    created_at: datetime,
) -> GcObservedActivityFullAggregate:
    strategy = build_gc_session_calendar_source_strategy_report(
        strategy_path,
        created_at=created_at,
    ).to_payload()
    if strategy["calendar_registration_allowed"] is not False:
        raise ValueError("strategy must not allow calendar registration")

    periods: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        entries = sorted(name for name in archive.namelist() if name.lower().endswith(".parquet"))
        if not entries:
            raise ValueError("no parquet entries found")
        for name in entries:
            parquet_file = pq.ParquetFile(io.BytesIO(archive.read(name)))
            first, last = _ts_event_stats(parquet_file)
            periods.append(
                {
                    "member": name,
                    "row_count": int(parquet_file.metadata.num_rows),
                    "first_observed_at": _utc_z(first),
                    "last_observed_at": _utc_z(last),
                }
            )

    ordered_periods = sorted(periods, key=lambda period: period["first_observed_at"])
    inter_member_gaps = [
        int(
            (
                pd.Timestamp(right["first_observed_at"])
                - pd.Timestamp(left["last_observed_at"])
            ).total_seconds()
        )
        for left, right in zip(ordered_periods, ordered_periods[1:])
    ]
    largest_gap = max(inter_member_gaps) if inter_member_gaps else 0
    row_count = sum(int(period["row_count"]) for period in ordered_periods)
    payload = {
        "aggregate_id": _id(
            {
                "created_at": utc_iso(created_at),
                "row_count": row_count,
                "periods": ordered_periods,
                "largest_inter_member_gap_seconds": largest_gap,
            }
        ),
        "aggregate_version": FULL_AGGREGATE_VERSION,
        "mode": FULL_AGGREGATE_MODE,
        "created_at": utc_iso(created_at),
        "status": "FULL_OBSERVED_ACTIVITY_AGGREGATE_READY_SESSION_CALENDAR_UNSATISFIED",
        "canonical_symbol": "GC",
        "local_path": REDACTED_LOCAL_PATH,
        "source_strategy_ref": SOURCE_STRATEGY_REF,
        "observed_activity_leg_status": "METADATA_ONLY_ZERO_COST_EVIDENCE_LEG",
        "metadata_only": True,
        "parquet_entry_count": len(ordered_periods),
        "row_count": int(row_count),
        "first_observed_at": ordered_periods[0]["first_observed_at"],
        "last_observed_at": ordered_periods[-1]["last_observed_at"],
        "largest_inter_member_gap_seconds": int(largest_gap),
        "periods": ordered_periods,
        "session_calendar_gate_status": "UNSATISFIED_OBSERVED_ACTIVITY_ONLY",
        "calendar_registration_allowed": False,
        "dataset_construction_allowed": False,
        "resampling_allowed": False,
        "training_allowed": False,
        "blocked_actions": list(OBSERVED_BLOCKED_ACTIONS),
        "blocked_reasons": list(OBSERVED_BLOCKED_REASONS),
    }
    return GcObservedActivityFullAggregate(payload=payload)

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.source_identity import (
    load_source_identity_policy,
    validate_source_identity,
)
from trading_system.features.contracts import utc_iso
from trading_system.research.readiness import APPROVED_DECISION, load_real_data_decisions

PROFILE_VERSION = "databento-gc-source-profile-0.1.0"
MODE = "DATABENTO_GC_ZIP_SOURCE_PROFILE"
READY_STATUS = "PROFILE_SAMPLED_DATASET_BLOCKED"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
CANONICAL_SYMBOL = "GC"
VENDOR = "DATABENTO"
RECOMMENDED_TIMEFRAME = "4h"
DAY_SESSION_POLICY_STATUS = "RESEARCH_DECISION_PENDING_MEASURE_FIRST"
HHLL_LABEL_ROLE = "AUXILIARY_DIRECTION_LABEL_ONLY"
CONTRACT_IDENTITY_STATUS = "UNDECLARED_PENDING_RESEARCH"
ROLL_POLICY_STATUS = "RESEARCH_DECISION_PENDING"
TS_EVENT_ROLE = "INTERVAL_START_NOT_BAR_CLOSE"
NO_TRADE_SECOND_POLICY = "ABSENT_ROW_UNTIL_RESAMPLING_POLICY_DEFINED"
FULL_ARCHIVE_QUALITY_STATUS = "NOT_PROVEN_IN_PHASE_20"
REQUIRED_COLUMNS = ("gc_open", "gc_high", "gc_low", "gc_close", "gc_volume")
BLOCKED_ACTIONS = (
    "BUILD_REAL_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "DEPLOYMENT",
    "RUN_OFFLINE_DRY_RUN",
    "RESAMPLE_PERSISTENT_DATASET",
    "COPY_RAW_SOURCE",
    "MUTATE_RAW_SOURCE",
    "UPLOAD_RAW_SOURCE",
    "INGEST_HHLL_DERIVED_LABELS",
)
REQUIRED_APPROVED_ITEMS = frozenset(
    {
        "REAL_HISTORICAL_OHLCV_CSV",
        "PRODUCTION_OHLCV_VENDOR_DECISION",
        "FIRST_REAL_SYMBOL",
        "FIRST_HISTORICAL_INTERVAL",
        "RAW_DATA_STORAGE_LICENSE_APPROVAL",
    }
)


@dataclass(frozen=True)
class DatabentoGcSourceProfile:
    profile_id: str
    created_at: datetime
    status: str
    zip_sha256: str | None
    source_id: str
    raw_symbol: str
    timeframe: str
    parquet_entry_count: int
    sampled_entry_count: int
    columns: tuple[str, ...]
    time_index_name: str | None
    time_index_timezone: str | None
    row_count: int
    first_observed_at: str | None
    last_observed_at: str | None
    source_identity: dict[str, Any]
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
            "source_id": self.source_id,
            "canonical_symbol": CANONICAL_SYMBOL,
            "raw_symbol": self.raw_symbol,
            "vendor": VENDOR,
            "timeframe": self.timeframe,
            "metadata_path": REDACTED_LOCAL_PATH,
            "decisions_path": REDACTED_LOCAL_PATH,
            "parquet_entry_count": self.parquet_entry_count,
            "sampled_entry_count": self.sampled_entry_count,
            "columns": list(self.columns),
            "time_index_name": self.time_index_name,
            "time_index_timezone": self.time_index_timezone,
            "row_count": self.row_count,
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "source_identity": self.source_identity,
            "recommended_timeframe": RECOMMENDED_TIMEFRAME,
            "day_session_policy_status": DAY_SESSION_POLICY_STATUS,
            "hhll_label_role": HHLL_LABEL_ROLE,
            "hhll_files_not_in_scope": True,
            "contract_identity_status": CONTRACT_IDENTITY_STATUS,
            "roll_policy_status": ROLL_POLICY_STATUS,
            "ts_event_role": TS_EVENT_ROLE,
            "no_trade_second_policy": NO_TRADE_SECOND_POLICY,
            "full_archive_quality_status": FULL_ARCHIVE_QUALITY_STATUS,
            "production_allowed": False,
            "dataset_construction_allowed": False,
            "training_allowed": False,
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _profile_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _utc_z(value: pd.Timestamp) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _decision_reasons(decisions_path: Path) -> list[str]:
    try:
        decision_file = load_real_data_decisions(decisions_path)
    except Exception:
        return ["INVALID_DECISIONS_FILE"]
    by_item = {decision.item_id: decision.decision for decision in decision_file.decisions}
    if any(by_item.get(item_id) != APPROVED_DECISION for item_id in REQUIRED_APPROVED_ITEMS):
        return ["MISSING_REQUIRED_DECISIONS"]
    return []


def _metadata_reasons(metadata: Any) -> list[str]:
    if not isinstance(metadata, dict):
        return ["INVALID_SOURCE_METADATA"]
    expected = {
        "source_type": "OHLCV_BAR",
        "canonical_symbol": CANONICAL_SYMBOL,
        "raw_symbol": CANONICAL_SYMBOL,
        "venue": VENDOR,
        "source_status": "OPEN_HUMAN_DECISION",
    }
    for field, value in expected.items():
        if str(metadata.get(field, "")).strip() != value:
            return ["INVALID_SOURCE_METADATA"]
    return []


def _frame_reasons(frame: pd.DataFrame) -> list[str]:
    reasons: list[str] = []
    if list(frame.columns) != list(REQUIRED_COLUMNS):
        return ["UNEXPECTED_COLUMNS"]
    index = frame.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.name != "ts_event"
        or index.tz is None
        or str(index.tz) != "UTC"
    ):
        reasons.append("INDEX_NOT_TS_EVENT_UTC")
        return reasons
    if not index.is_monotonic_increasing:
        reasons.append("NON_MONOTONIC_INDEX")
    if index.has_duplicates:
        reasons.append("DUPLICATE_TIMESTAMPS")
    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        reasons.append("NULL_VALUES_PRESENT")
        return reasons
    invalid_ohlc = (
        (frame["gc_high"] < frame["gc_low"])
        | (frame["gc_high"] < frame[["gc_open", "gc_close"]].max(axis=1))
        | (frame["gc_low"] > frame[["gc_open", "gc_close"]].min(axis=1))
    )
    if bool(invalid_ohlc.any()):
        reasons.append("INVALID_OHLC")
    if bool((frame["gc_volume"] < 0).any()):
        reasons.append("NEGATIVE_VOLUME")
    return reasons


def build_databento_gc_source_profile(
    zip_path: Path,
    metadata_path: Path,
    decisions_path: Path,
    *,
    created_at: datetime,
    max_sample_entries: int = 3,
) -> DatabentoGcSourceProfile:
    reasons: list[str] = []
    metadata: dict[str, Any] = {}
    try:
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        reasons.append("INVALID_SOURCE_METADATA")
    else:
        reasons.extend(_metadata_reasons(metadata))
        if not isinstance(metadata, dict):
            metadata = {}
    reasons.extend(_decision_reasons(decisions_path))

    source_identity: dict[str, Any] = {
        "status": "BLOCKED",
        "production_allowed": False,
        "blocked_reasons": ["SOURCE_IDENTITY_UNAVAILABLE"],
    }
    try:
        identity_policy = load_source_identity_policy(
            Path(__file__).resolve().parents[2] / "configs/data/source-identity-policy.yaml"
        )
        source_identity = validate_source_identity(metadata, identity_policy).to_payload()
    except Exception:
        reasons.append("INVALID_SOURCE_METADATA")
    if source_identity.get("status") == "FIXTURE_ONLY":
        source_identity = {
            **source_identity,
            "status": "BLOCKED",
            "blocked_reasons": [
                *source_identity.get("blocked_reasons", []),
                "FIXTURE_SOURCE_NOT_ALLOWED",
            ],
        }
    if source_identity.get("status") != "REAL_SOURCE_PENDING_HUMAN_DECISION":
        reasons.append("SOURCE_IDENTITY_NOT_PENDING_REAL_SOURCE")

    zip_sha256: str | None = None
    parquet_entry_count = 0
    sampled_entry_count = 0
    columns: tuple[str, ...] = ()
    time_index_name: str | None = None
    time_index_timezone: str | None = None
    row_count = 0
    first_observed_at: str | None = None
    last_observed_at: str | None = None

    try:
        zip_sha256 = sha256_file(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            entries = sorted(
                name for name in archive.namelist() if name.lower().endswith(".parquet")
            )
            parquet_entry_count = len(entries)
            if not entries:
                reasons.append("EMPTY_ARCHIVE")
            else:
                sample_names = list(dict.fromkeys([entries[0], entries[len(entries) // 2], entries[-1]]))
                sample_names = sample_names[:max_sample_entries]
                sampled_entry_count = len(sample_names)
                sampled_frames: dict[str, pd.DataFrame] = {}
                for name in sample_names:
                    frame = pd.read_parquet(io.BytesIO(archive.read(name)), engine="pyarrow")
                    sampled_frames[name] = frame
                    for reason in _frame_reasons(frame):
                        if reason not in reasons:
                            reasons.append(reason)
                first_frame = sampled_frames[sample_names[0]]
                columns = tuple(str(column) for column in first_frame.columns)
                if isinstance(first_frame.index, pd.DatetimeIndex):
                    time_index_name = first_frame.index.name
                    time_index_timezone = str(first_frame.index.tz) if first_frame.index.tz else None
                if "UNEXPECTED_COLUMNS" not in reasons:
                    for name in entries:
                        close_only = pd.read_parquet(
                            io.BytesIO(archive.read(name)), engine="pyarrow", columns=["gc_close"]
                        )
                        row_count += len(close_only)
                edge_first = sampled_frames[entries[0]] if entries[0] in sampled_frames else None
                edge_last = sampled_frames[entries[-1]] if entries[-1] in sampled_frames else None
                if (
                    edge_first is not None
                    and edge_last is not None
                    and isinstance(edge_first.index, pd.DatetimeIndex)
                    and isinstance(edge_last.index, pd.DatetimeIndex)
                    and len(edge_first.index) > 0
                    and len(edge_last.index) > 0
                    and edge_first.index.tz is not None
                    and edge_last.index.tz is not None
                ):
                    first_observed_at = _utc_z(edge_first.index.min())
                    last_observed_at = _utc_z(edge_last.index.max())
    except (OSError, zipfile.BadZipFile):
        reasons.append("UNREADABLE_ZIP")
    except Exception:
        reasons.append("PROFILE_PREPARATION_FAILED")

    unique_reasons = tuple(dict.fromkeys(reasons))
    status = READY_STATUS if not unique_reasons else "BLOCKED"
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "zip_sha256": zip_sha256,
        "parquet_entry_count": parquet_entry_count,
        "row_count": row_count,
        "first_observed_at": first_observed_at,
        "last_observed_at": last_observed_at,
        "blocked_reasons": list(unique_reasons),
    }
    return DatabentoGcSourceProfile(
        profile_id=_profile_id(id_payload),
        created_at=created_at,
        status=status,
        zip_sha256=zip_sha256,
        source_id=str(metadata.get("source_id", "UNKNOWN_SOURCE")),
        raw_symbol=str(metadata.get("raw_symbol", CANONICAL_SYMBOL)),
        timeframe=str(metadata.get("timeframe", "1s")),
        parquet_entry_count=parquet_entry_count,
        sampled_entry_count=sampled_entry_count,
        columns=columns,
        time_index_name=time_index_name,
        time_index_timezone=time_index_timezone,
        row_count=row_count,
        first_observed_at=first_observed_at,
        last_observed_at=last_observed_at,
        source_identity=source_identity,
        blocked_reasons=unique_reasons,
    )

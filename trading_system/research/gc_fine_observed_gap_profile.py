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

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research.gc_session_calendar_source_strategy import (
    OBSERVED_BLOCKED_ACTIONS,
    REDACTED_LOCAL_PATH,
    SOURCE_STRATEGY_REF,
    build_gc_session_calendar_source_strategy_report,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_VERSION = "gc-fine-observed-gap-profile-0.1.0"
MODE = "GC_FINE_OBSERVED_GAP_PROFILE"
SCHEMA_PATH = ROOT / "schemas/gc_fine_observed_gap_profile.schema.json"
BLOCKED_REASONS = (
    "OBSERVED_GAPS_NOT_CALENDAR_AUTHORITY",
    "SESSION_CALENDAR_GATE_UNSATISFIED",
    "SCHEDULED_VS_OBSERVED_RECONCILIATION_NOT_IMPLEMENTED",
    "ERA_VERSIONED_OVERLAY_NOT_IMPLEMENTED",
)
EXPECTED_CADENCE_SECONDS = 1


@dataclass(frozen=True)
class GcFineObservedGapProfile:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _utc_z(value: pd.Timestamp) -> str:
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    else:
        value = value.tz_convert("UTC")
    return value.isoformat().replace("+00:00", "Z")


def _read_ts_event_series(raw: bytes) -> tuple[pd.Series, str]:
    table = pq.read_table(io.BytesIO(raw), columns=["ts_event"])
    values = table.column("ts_event").to_pandas()
    if values.empty:
        raise ValueError("fine observed gap profile requires non-empty ts_event")
    timestamps = pd.Series(pd.to_datetime(values, utc=True))
    if timestamps.is_monotonic_increasing:
        return timestamps.reset_index(drop=True), "ALREADY_MONOTONIC"
    return timestamps.sort_values(ignore_index=True), "SORTED_FOR_PROFILE"


def _period_gap_summary(
    member: str,
    timestamps: pd.Series,
    *,
    timestamp_order_status: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    diffs = timestamps.diff()
    gap_seconds = diffs.dt.total_seconds()
    gap_mask = gap_seconds > EXPECTED_CADENCE_SECONDS
    gap_rows = pd.DataFrame(
        {
            "left_observed_at": timestamps.shift(1)[gap_mask],
            "right_observed_at": timestamps[gap_mask],
            "gap_seconds": gap_seconds[gap_mask].astype("int64"),
        }
    )
    gaps = [
        {
            "member": member,
            "left_observed_at": _utc_z(pd.Timestamp(row.left_observed_at)),
            "right_observed_at": _utc_z(pd.Timestamp(row.right_observed_at)),
            "gap_seconds": int(row.gap_seconds),
        }
        for row in gap_rows.itertuples(index=False)
    ]
    summary = {
        "member": member,
        "row_count": int(len(timestamps)),
        "first_observed_at": _utc_z(pd.Timestamp(timestamps.iloc[0])),
        "last_observed_at": _utc_z(pd.Timestamp(timestamps.iloc[-1])),
        "timestamp_order_status": timestamp_order_status,
        "largest_gap_seconds": max((gap["gap_seconds"] for gap in gaps), default=0),
        "nonconsecutive_transition_count": len(gaps),
    }
    return summary, gaps


def build_gc_fine_observed_gap_profile(
    zip_path: Path,
    strategy_path: Path,
    *,
    created_at: datetime,
    top_n_gaps: int = 20,
    max_members: int | None = None,
) -> GcFineObservedGapProfile:
    strategy = build_gc_session_calendar_source_strategy_report(
        strategy_path,
        created_at=created_at,
    ).to_payload()
    if strategy["calendar_registration_allowed"] is not False:
        raise ValueError("strategy must not allow calendar registration")
    if top_n_gaps < 0:
        raise ValueError("top_n_gaps must be non-negative")
    if max_members is not None and max_members <= 0:
        raise ValueError("max_members must be positive when provided")

    periods: list[dict[str, Any]] = []
    all_gaps: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        entries = sorted(name for name in archive.namelist() if name.lower().endswith(".parquet"))
        if not entries:
            raise ValueError("no parquet entries found")
        if max_members is not None:
            entries = entries[:max_members]
        for name in entries:
            timestamps, timestamp_order_status = _read_ts_event_series(archive.read(name))
            summary, gaps = _period_gap_summary(
                name,
                timestamps,
                timestamp_order_status=timestamp_order_status,
            )
            periods.append(summary)
            all_gaps.extend(gaps)

    top_gaps = sorted(
        all_gaps,
        key=lambda gap: (-int(gap["gap_seconds"]), str(gap["member"]), str(gap["left_observed_at"])),
    )[:top_n_gaps]
    row_count = sum(int(period["row_count"]) for period in periods)
    body = {
        "profile_version": PROFILE_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "FINE_OBSERVED_GAP_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED",
        "canonical_symbol": "GC",
        "local_path": REDACTED_LOCAL_PATH,
        "source_strategy_ref": SOURCE_STRATEGY_REF,
        "timestamp_column_only": True,
        "expected_cadence_seconds": EXPECTED_CADENCE_SECONDS,
        "parquet_entry_count": len(periods),
        "row_count": int(row_count),
        "largest_gap_seconds": max((int(gap["gap_seconds"]) for gap in all_gaps), default=0),
        "nonconsecutive_transition_count": len(all_gaps),
        "periods": periods,
        "top_gaps": top_gaps,
        "session_calendar_gate_status": "UNSATISFIED_OBSERVED_GAP_PROFILE_ONLY",
        "calendar_registration_allowed": False,
        "dataset_construction_allowed": False,
        "resampling_allowed": False,
        "training_allowed": False,
        "blocked_actions": list(OBSERVED_BLOCKED_ACTIONS),
        "blocked_reasons": list(BLOCKED_REASONS),
    }
    payload = {"profile_id": _id(body), **body}
    return GcFineObservedGapProfile(payload=payload)

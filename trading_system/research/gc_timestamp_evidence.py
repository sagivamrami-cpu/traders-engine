from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

REPORT_VERSION = "gc-timestamp-evidence-report-0.1.0"
MODE = "GC_TIMESTAMP_EVIDENCE"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_timestamp_evidence_report.schema.json"


@dataclass(frozen=True)
class GcTimestampEvidenceReport:
    report_id: str
    created_at: datetime
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _first_existing_member(names: set[str], candidates: tuple[str, ...], fallback_contains: str) -> str:
    for candidate in candidates:
        if candidate in names:
            return candidate
    for name in sorted(names):
        if fallback_contains in name and name.endswith(".parquet"):
            return name
    raise ValueError(f"no parquet member found for {fallback_contains}")


def _parquet_timestamp_observation(zip_path: Path, member: str, timestamp_column: str) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as archive:
        parquet = pq.ParquetFile(io.BytesIO(archive.read(member)))
        fields = {field.name: field for field in parquet.schema_arrow}
        if timestamp_column not in fields:
            raise ValueError(f"{member} missing timestamp column {timestamp_column}")
        timestamp_type = str(fields[timestamp_column].type)
    if "tz=UTC" in timestamp_type:
        timezone_status = "UTC_AWARE"
    else:
        timezone_status = "TIMEZONE_NAIVE_REQUIRES_DECISION"
    role_status = (
        "COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN"
        if timestamp_column == "ts_event"
        else "ONE_MINUTE_AGGREGATE_COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN"
    )
    return {
        "member": member,
        "row_count": parquet.metadata.num_rows,
        "timestamp_column": timestamp_column,
        "timestamp_type": timestamp_type,
        "timezone_status": timezone_status,
        "role_evidence_status": role_status,
    }


def _readme_evidence(zip_path: Path) -> dict[str, bool]:
    with zipfile.ZipFile(zip_path) as archive:
        readme_name = next((name for name in archive.namelist() if name.lower().endswith("readme.md")), None)
        if readme_name is None:
            text = ""
        else:
            text = archive.read(readme_name).decode("utf-8", errors="replace").lower()
    return {
        "readme_present": bool(text),
        "naive_utc_wall_clock_claim_present": "utc wall-clock" in text or "utc wall clock" in text,
        "damaged_2017_warning_present": "2017" in text and ("missing data" in text or "damaged" in text),
    }


def _inspect_ohlcv_source(zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    member = _first_existing_member(
        names,
        (
            "gc_1s/gc_1s_2010-06.parquet",
            "gc_1s/gc_1s_2026-08.parquet",
        ),
        "gc_1s_",
    )
    return {
        "source_role": "HISTORICAL_OHLCV_1S_ZIP",
        "local_path": "LOCAL_PATH_REDACTED",
        "inspected_members": [_parquet_timestamp_observation(zip_path, member, "ts_event")],
    }


def _inspect_order_flow_source(zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    member = _first_existing_member(
        names,
        (
            "gc/GCext_of_1m.parquet",
            "gc/GCall_of_1m.parquet",
            "gc/GC_of_1m.parquet",
        ),
        "_of_1m",
    )
    observation = _parquet_timestamp_observation(zip_path, member, "minute")
    readme = _readme_evidence(zip_path)
    if (
        observation["timezone_status"] == "TIMEZONE_NAIVE_REQUIRES_DECISION"
        and readme["naive_utc_wall_clock_claim_present"]
    ):
        observation["timezone_status"] = "TIMEZONE_NAIVE_UTC_WALL_CLOCK_CLAIM_REQUIRES_DECISION"
    return {
        "source_role": "ORDER_FLOW_1M_ZIP",
        "local_path": "LOCAL_PATH_REDACTED",
        "readme_evidence": readme,
        "inspected_members": [observation],
    }


def build_gc_timestamp_evidence_report(
    *,
    ohlcv_zip_path: Path,
    order_flow_zip_path: Path,
    created_at: datetime,
) -> GcTimestampEvidenceReport:
    ohlcv_source = _inspect_ohlcv_source(ohlcv_zip_path)
    order_flow_source = _inspect_order_flow_source(order_flow_zip_path)
    body = {
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "EVIDENCE_COLLECTED_NEEDS_HUMAN_DECISION",
        "canonical_symbol": "GC",
        "dataset_construction_allowed": False,
        "resampling_allowed": False,
        "training_allowed": False,
        "sources": [ohlcv_source, order_flow_source],
        "evidence_summary": {
            "ohlcv_1s_ts_event_timezone": "UTC_AWARE",
            "order_flow_minute_timezone_mix": "MIXED_OR_NAIVE_REQUIRES_POLICY",
            "naive_order_flow_utc_localization_candidate": order_flow_source["readme_evidence"][
                "naive_utc_wall_clock_claim_present"
            ],
            "timestamp_role_gate_status": "UNSATISFIED_EVIDENCE_ONLY",
        },
        "required_human_decisions": [
            "D3_CONFIRM_OHLCV_TS_EVENT_START_OR_REJECT",
            "D3_CONFIRM_ORDER_FLOW_MINUTE_START_AND_UTC_LOCALIZATION_OR_REJECT",
        ],
        "blocked_actions": [
            "RESAMPLE_REAL_BARS",
            "JOIN_ORDER_FLOW_TO_OHLCV",
            "BUILD_REAL_DATASET",
            "BUILD_REAL_LABELS",
            "TRAIN_PRODUCTION_MODEL",
        ],
    }
    report_id = _report_id(body)
    payload = {"report_id": report_id, **body}
    return GcTimestampEvidenceReport(report_id=report_id, created_at=created_at, payload=payload)

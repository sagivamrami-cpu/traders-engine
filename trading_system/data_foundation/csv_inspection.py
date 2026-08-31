from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from trading_system.data_foundation.csv_onboarding import REQUIRED_OHLCV_COLUMNS
from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.normalization import NormalizationPolicy, parse_datetime, read_csv_rows
from trading_system.features.contracts import utc_iso

INSPECTION_VERSION = "local-csv-inspection-report-0.1.0"
MODE = "LOCAL_OHLCV_CSV_INSPECTION"


@dataclass(frozen=True)
class LocalCsvInspectionReport:
    inspection_id: str
    created_at: datetime
    status: str
    csv_path: Path
    raw_file_sha256: str
    row_count: int
    required_columns_present: bool
    missing_columns: tuple[str, ...]
    raw_symbols: tuple[str, ...]
    first_observed_at: str | None
    last_observed_at: str | None
    suggested_metadata: dict[str, Any] | None
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "inspection_id": self.inspection_id,
            "inspection_version": INSPECTION_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": str(self.csv_path),
            "raw_file_sha256": self.raw_file_sha256,
            "row_count": self.row_count,
            "required_columns_present": self.required_columns_present,
            "missing_columns": list(self.missing_columns),
            "raw_symbols": list(self.raw_symbols),
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "suggested_metadata": self.suggested_metadata,
            "blocked_reasons": list(self.blocked_reasons),
        }


def _suggested_metadata(inputs: Mapping[str, str], raw_symbol: str, timezone: str) -> dict[str, Any]:
    return {
        "manifest_version": "raw-source-manifest-0.1.0",
        "source_id": inputs["source_id"],
        "source_type": "OHLCV_BAR",
        "source_status": "OPEN_HUMAN_DECISION",
        "asset_class": inputs["asset_class"],
        "venue": inputs["venue"],
        "canonical_symbol": inputs["canonical_symbol"],
        "raw_symbol": raw_symbol,
        "timeframe": inputs["timeframe"],
        "timezone": timezone,
        "session_calendar_id": inputs["session_calendar_id"],
        "schema_version": "local-csv-ohlcv-schema-0.1.0",
        "correction_policy": "corrections_preserve_available_at",
        "owner": inputs["owner"],
    }


def _inspection_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def inspect_local_ohlcv_csv(
    csv_path: Path,
    metadata_inputs: Mapping[str, str],
    policy: NormalizationPolicy,
    *,
    created_at: datetime,
) -> LocalCsvInspectionReport:
    rows = read_csv_rows(csv_path)
    row_count = len(rows)
    columns = set(rows[0]) if rows else set()
    missing_columns = tuple(sorted(REQUIRED_OHLCV_COLUMNS - columns))
    required_columns_present = not missing_columns
    raw_symbols = tuple(sorted({row["raw_symbol"] for row in rows if row.get("raw_symbol")}))
    blocked_reasons: list[str] = []
    first_observed_at = None
    last_observed_at = None
    suggested_metadata = None

    if row_count == 0:
        blocked_reasons.append("CSV_HAS_NO_ROWS")
    if missing_columns:
        blocked_reasons.append("MISSING_REQUIRED_COLUMNS")
    if len(raw_symbols) > 1:
        blocked_reasons.append("MULTIPLE_RAW_SYMBOLS_REQUIRE_SPLIT")

    if required_columns_present and row_count > 0:
        observed_times = [parse_datetime(row["timestamp"], policy.source_timezone) for row in rows]
        first_observed_at = utc_iso(min(observed_times))
        last_observed_at = utc_iso(max(observed_times))
    if required_columns_present and row_count > 0 and len(raw_symbols) == 1:
        suggested_metadata = _suggested_metadata(metadata_inputs, raw_symbols[0], policy.source_timezone)

    status = "READY_FOR_BUNDLE_VALIDATION" if not blocked_reasons else "BLOCKED"
    id_payload = {
        "created_at": utc_iso(created_at),
        "csv_path": str(csv_path),
        "raw_file_sha256": sha256_file(csv_path),
        "row_count": row_count,
        "raw_symbols": raw_symbols,
        "status": status,
    }
    return LocalCsvInspectionReport(
        inspection_id=_inspection_id(id_payload),
        created_at=created_at,
        status=status,
        csv_path=csv_path,
        raw_file_sha256=str(id_payload["raw_file_sha256"]),
        row_count=row_count,
        required_columns_present=required_columns_present,
        missing_columns=missing_columns,
        raw_symbols=raw_symbols,
        first_observed_at=first_observed_at,
        last_observed_at=last_observed_at,
        suggested_metadata=suggested_metadata,
        blocked_reasons=tuple(blocked_reasons),
    )

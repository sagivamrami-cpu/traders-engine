from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from trading_system.data_foundation.csv_onboarding import REQUIRED_OHLCV_COLUMNS
from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.normalization import NormalizationPolicy, SymbolMap, parse_datetime, read_csv_rows
from trading_system.features.contracts import utc_iso

INSPECTION_VERSION = "local-csv-inspection-report-0.2.0"
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
    symbol_map: SymbolMap | None = None,
    *,
    created_at: datetime,
) -> LocalCsvInspectionReport:
    rows = read_csv_rows(csv_path)
    row_count = len(rows)
    columns = set(rows[0]) if rows else set()
    missing_columns = tuple(sorted(REQUIRED_OHLCV_COLUMNS - columns))
    required_columns_present = not missing_columns
    raw_symbols = tuple(sorted({row["raw_symbol"].strip() for row in rows if row.get("raw_symbol", "").strip()}))
    blocked_reasons: list[str] = []
    first_observed_at = None
    last_observed_at = None
    suggested_metadata = None

    def add_reason(reason: str) -> None:
        if reason not in blocked_reasons:
            blocked_reasons.append(reason)

    if row_count == 0:
        add_reason("CSV_HAS_NO_ROWS")
    if missing_columns:
        add_reason("MISSING_REQUIRED_COLUMNS")
    if len(raw_symbols) > 1:
        add_reason("MULTIPLE_RAW_SYMBOLS_REQUIRE_SPLIT")

    if required_columns_present and row_count > 0:
        observed_times = []
        seen_observed_keys: set[tuple[str, str]] = set()
        for row in rows:
            raw_symbol = row.get("raw_symbol", "").strip()
            if not raw_symbol:
                add_reason("RAW_SYMBOL_REQUIRED")
                continue
            if symbol_map is not None:
                canonical = symbol_map.raw_to_canonical.get(raw_symbol)
                if canonical is None:
                    add_reason("UNKNOWN_RAW_SYMBOL")
                elif canonical != metadata_inputs["canonical_symbol"]:
                    add_reason("CANONICAL_SYMBOL_MISMATCH")
            try:
                observed_at = parse_datetime(row["timestamp"], policy.source_timezone)
                available_at = parse_datetime(row["available_at"], policy.source_timezone)
            except (KeyError, ValueError):
                add_reason("DATETIME_PARSE_FAILED")
                continue
            observed_times.append(observed_at)
            observed_key = (raw_symbol, utc_iso(observed_at))
            if observed_key in seen_observed_keys:
                add_reason("DUPLICATE_TIMESTAMPS")
            seen_observed_keys.add(observed_key)
            if available_at < observed_at:
                add_reason("AVAILABLE_AT_BEFORE_OBSERVED_AT")
            try:
                open_price = float(row["open"])
                high = float(row["high"])
                low = float(row["low"])
                close = float(row["close"])
            except (KeyError, ValueError):
                add_reason("INVALID_OHLC")
                continue
            if high < low or high < max(open_price, close) or low > min(open_price, close):
                add_reason("INVALID_OHLC")
        if observed_times:
            first_observed_at = utc_iso(min(observed_times))
            last_observed_at = utc_iso(max(observed_times))
    if required_columns_present and row_count > 0 and len(raw_symbols) == 1 and not blocked_reasons:
        suggested_metadata = _suggested_metadata(metadata_inputs, raw_symbols[0], policy.source_timezone)

    status = "SHAPE_VALIDATED_NEEDS_BUNDLE_VALIDATION" if not blocked_reasons else "BLOCKED"
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

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.normalization import (
    NormalizationPolicy,
    SymbolMap,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.data_foundation.source_identity import load_source_identity_policy, validate_source_identity

REQUIRED_OHLCV_COLUMNS = frozenset(
    {
        "raw_symbol",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "correction_status",
        "available_at",
    }
)
ROOT = Path(__file__).resolve().parents[2]


class CsvOnboardingError(ValueError):
    pass


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise CsvOnboardingError("datetime must be timezone-aware")
    return value.isoformat().replace("+00:00", "Z")


def _validate_columns(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise CsvOnboardingError("csv contains no rows")
    columns = set(rows[0])
    missing = sorted(REQUIRED_OHLCV_COLUMNS - columns)
    if missing:
        raise CsvOnboardingError(f"missing required columns: {', '.join(missing)}")


def build_raw_source_manifest_for_csv(
    csv_path: Path,
    metadata: Mapping[str, Any],
    policy: NormalizationPolicy,
    symbol_map: SymbolMap,
    *,
    ingested_at: datetime,
    project_root: Path | None = None,
) -> dict[str, Any]:
    identity_policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    identity = validate_source_identity(metadata, identity_policy, project_root=project_root)
    if identity.status == "BLOCKED":
        raise CsvOnboardingError(", ".join(identity.blocked_reasons))
    if identity.status != "FIXTURE_ONLY":
        raise CsvOnboardingError("REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED")

    rows = read_csv_rows(csv_path)
    _validate_columns(rows)

    try:
        records = [
            normalize_ohlcv_row(
                row,
                policy,
                symbol_map,
                source_id=str(metadata["source_id"]),
                source_version=str(metadata["schema_version"]),
            )
            for row in rows
        ]
    except Exception as exc:
        raise CsvOnboardingError(str(exc)) from exc

    canonical_symbol = str(metadata["canonical_symbol"])
    observed_symbols = {record.canonical_symbol for record in records}
    if observed_symbols != {canonical_symbol}:
        raise CsvOnboardingError(
            "csv canonical symbols do not match metadata canonical_symbol: "
            + ", ".join(sorted(observed_symbols))
        )

    observed_at_values = [record.observed_at for record in records]

    return {
        "manifest_version": metadata["manifest_version"],
        "source_id": metadata["source_id"],
        "source_type": metadata["source_type"],
        "source_status": metadata["source_status"],
        "asset_class": metadata["asset_class"],
        "venue": metadata["venue"],
        "canonical_symbol": metadata["canonical_symbol"],
        "raw_symbol": metadata["raw_symbol"],
        "timeframe": metadata["timeframe"],
        "timezone": metadata["timezone"],
        "session_calendar_id": metadata["session_calendar_id"],
        "schema_version": metadata["schema_version"],
        "raw_file": str(csv_path),
        "raw_file_sha256": sha256_file(csv_path),
        "row_count": len(rows),
        "first_observed_at": _format_utc(min(observed_at_values)),
        "last_observed_at": _format_utc(max(observed_at_values)),
        "ingested_at": _format_utc(ingested_at),
        "correction_policy": metadata["correction_policy"],
        "owner": metadata["owner"],
    }

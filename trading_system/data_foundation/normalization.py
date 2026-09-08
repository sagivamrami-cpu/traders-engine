from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import yaml

from trading_system.data_foundation.contracts import (
    CorrectionStatus,
    NormalizedBar,
    QualityStatus,
)


class UnknownSymbolError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizationPolicy:
    version: str
    source_timezone: str
    stale_after_seconds: int
    missing_volume_status: QualityStatus


@dataclass(frozen=True)
class SymbolMap:
    version: str
    raw_to_canonical: Mapping[str, str]


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_normalization_policy(path: Path) -> NormalizationPolicy:
    data = load_yaml(path)
    return NormalizationPolicy(
        version=data["version"],
        source_timezone=data["timestamp_policy"]["source_timezone"],
        stale_after_seconds=int(data["quality_policy"]["stale_after_seconds"]),
        missing_volume_status=QualityStatus(data["quality_policy"]["missing_volume_status"]),
    )


def load_symbol_map(path: Path) -> SymbolMap:
    data = load_yaml(path)
    raw_to_canonical: dict[str, str] = {}
    for symbol in data["symbols"]:
        canonical = symbol["canonical_symbol"]
        for raw_symbol in symbol["raw_symbols"]:
            raw_to_canonical[raw_symbol] = canonical
    return SymbolMap(version=data["version"], raw_to_canonical=raw_to_canonical)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_datetime(value: str, source_timezone: str) -> datetime:
    if not value:
        raise ValueError("datetime value is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
    return parsed.astimezone(UTC)


def map_symbol(raw_symbol: str, symbol_map: SymbolMap) -> str:
    try:
        return symbol_map.raw_to_canonical[raw_symbol]
    except KeyError as exc:
        raise UnknownSymbolError(f"Unknown raw symbol: {raw_symbol}") from exc


def _parse_float(value: str, field_name: str) -> float:
    if value == "":
        raise ValueError(f"{field_name} is required")
    return float(value)


def _parse_volume(value: str) -> float | None:
    return None if value == "" else float(value)


def normalize_ohlcv_row(
    row: Mapping[str, str],
    policy: NormalizationPolicy,
    symbol_map: SymbolMap,
    *,
    source_id: str,
    source_version: str,
) -> NormalizedBar:
    observed_at = parse_datetime(row["timestamp"], policy.source_timezone)
    available_at = parse_datetime(row["available_at"], policy.source_timezone)
    canonical_symbol = map_symbol(row["raw_symbol"], symbol_map)

    open_price = _parse_float(row["open"], "open")
    high = _parse_float(row["high"], "high")
    low = _parse_float(row["low"], "low")
    close = _parse_float(row["close"], "close")
    volume = _parse_volume(row["volume"])
    correction_status = CorrectionStatus(row["correction_status"])

    reason_codes: list[str] = []
    quality_status = QualityStatus.VALID

    if high < low:
        quality_status = QualityStatus.INVALID
        reason_codes.append("HIGH_BELOW_LOW")
    elif volume is None:
        quality_status = policy.missing_volume_status
        reason_codes.append("MISSING_VOLUME")
    elif correction_status is CorrectionStatus.CORRECTED:
        quality_status = QualityStatus.CORRECTED
        reason_codes.append("SOURCE_CORRECTION")
    elif (available_at - observed_at).total_seconds() > policy.stale_after_seconds:
        quality_status = QualityStatus.STALE
        reason_codes.append("AVAILABLE_AFTER_STALE_THRESHOLD")

    return NormalizedBar(
        source_id=source_id,
        source_version=source_version,
        raw_symbol=row["raw_symbol"],
        canonical_symbol=canonical_symbol,
        observed_at=observed_at,
        available_at=available_at,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        quality_status=quality_status,
        correction_status=correction_status,
        reason_codes=tuple(reason_codes),
    )

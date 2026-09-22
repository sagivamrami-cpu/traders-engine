from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping


class QualityStatus(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    STALE = "STALE"
    CORRECTED = "CORRECTED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class CorrectionStatus(str, Enum):
    ORIGINAL = "ORIGINAL"
    CORRECTED = "CORRECTED"


@dataclass(frozen=True)
class RawBar:
    source_id: str
    source_version: str
    raw_symbol: str
    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    correction_status: str
    available_at: str


@dataclass(frozen=True)
class NormalizedBar:
    source_id: str
    source_version: str
    raw_symbol: str
    canonical_symbol: str
    observed_at: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    quality_status: QualityStatus
    correction_status: CorrectionStatus
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    session_id: str | None = None


@dataclass(frozen=True)
class AvailabilityInterval:
    source_id: str
    canonical_symbol: str
    start_observed_at: datetime
    end_observed_at: datetime
    quality_status: QualityStatus
    reason_codes: tuple[str, ...]
    record_count: int


@dataclass(frozen=True)
class RawSourceManifest:
    manifest_version: str
    source_id: str
    source_type: str
    source_status: str
    asset_class: str
    venue: str
    canonical_symbol: str
    raw_symbol: str
    timeframe: str
    timezone: str
    session_calendar_id: str
    schema_version: str
    raw_file: str
    raw_file_sha256: str
    row_count: int
    first_observed_at: str
    last_observed_at: str
    ingested_at: str
    correction_policy: str
    owner: str


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    dataset_version: str
    created_at: str
    phase: int
    source_hashes: Mapping[str, str]
    normalization_policy_version: str
    session_calendar_version: str
    symbol_map_version: str
    date_ranges: Mapping[str, Mapping[str, str]]
    record_count: int
    availability_summary: Mapping[str, Any]
    quality_status_counts: Mapping[str, int]
    replay_fingerprint: str

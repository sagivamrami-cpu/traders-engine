from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.availability import build_availability_intervals
from trading_system.data_foundation.contracts import DatasetManifest
from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)


FIXED_PHASE1_CREATED_AT = "2026-08-31T00:00:00Z"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_phase1_dataset_manifest(root: Path) -> DatasetManifest:
    source_inventory = load_yaml(root / "configs/data/source-inventory.yaml")
    session_calendar = load_yaml(root / "configs/data/session-calendar.yaml")
    symbol_map_config = load_yaml(root / "configs/data/symbol-map.yaml")
    normalization_policy = load_normalization_policy(root / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(root / "configs/data/symbol-map.yaml")

    fixture_source = next(
        source
        for source in source_inventory["sources"]
        if source["source_status"] == "APPROVED_FIXTURE"
    )
    raw_path = root / fixture_source["raw_file"]
    raw_hash = sha256_file(raw_path)
    records = [
        normalize_ohlcv_row(
            row,
            normalization_policy,
            symbol_map,
            source_id=fixture_source["source_id"],
            source_version=fixture_source["schema_version"],
        )
        for row in read_csv_rows(raw_path)
    ]
    records = sorted(records, key=lambda record: record.observed_at)
    intervals = build_availability_intervals(records)
    quality_counts = Counter(record.quality_status.value for record in records)
    all_statuses = ["VALID", "MISSING", "STALE", "CORRECTED", "INVALID", "UNKNOWN"]
    quality_status_counts = {status: int(quality_counts.get(status, 0)) for status in all_statuses}
    observed_values = [record.observed_at for record in records]
    availability_summary = {
        "interval_count": len(intervals),
        "first_available_at": min(record.available_at for record in records).isoformat().replace("+00:00", "Z"),
        "last_available_at": max(record.available_at for record in records).isoformat().replace("+00:00", "Z"),
    }
    date_ranges = {
        fixture_source["source_id"]: {
            "first_observed_at": min(observed_values).isoformat().replace("+00:00", "Z"),
            "last_observed_at": max(observed_values).isoformat().replace("+00:00", "Z"),
        }
    }

    fingerprint_payload = {
        "source_hashes": {fixture_source["source_id"]: raw_hash},
        "normalization_policy_version": normalization_policy.version,
        "session_calendar_version": session_calendar["version"],
        "symbol_map_version": symbol_map_config["version"],
        "date_ranges": date_ranges,
        "quality_status_counts": quality_status_counts,
    }
    replay_fingerprint = hashlib.sha256(
        stable_json_dumps(fingerprint_payload).encode("utf-8")
    ).hexdigest()

    manifest = DatasetManifest(
        dataset_id="phase1-fixture-dataset",
        dataset_version="phase1-fixture-dataset-0.1.0",
        created_at=FIXED_PHASE1_CREATED_AT,
        phase=1,
        source_hashes={fixture_source["source_id"]: raw_hash},
        normalization_policy_version=normalization_policy.version,
        session_calendar_version=session_calendar["version"],
        symbol_map_version=symbol_map_config["version"],
        date_ranges=date_ranges,
        record_count=len(records),
        availability_summary=availability_summary,
        quality_status_counts=quality_status_counts,
        replay_fingerprint=replay_fingerprint,
    )
    return manifest


def build_phase1_dataset_payload(root: Path) -> dict[str, Any]:
    return to_plain_data(build_phase1_dataset_manifest(root))

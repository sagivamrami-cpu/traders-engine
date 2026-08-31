from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.availability import build_availability_intervals
from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.data_foundation.replay import build_phase1_dataset_payload


def load_yaml(relative_path: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def validate_schema_file(relative_path: str) -> None:
    Draft202012Validator.check_schema(load_json(relative_path))


def validate_data_configs() -> None:
    inventory = load_yaml("configs/data/source-inventory.yaml")
    calendars = load_yaml("configs/data/session-calendar.yaml")
    symbol_map = load_yaml("configs/data/symbol-map.yaml")
    normalization_policy = load_yaml("configs/data/normalization-policy.yaml")

    if not inventory.get("version"):
        raise ValueError("source inventory version is required")
    if not calendars.get("version"):
        raise ValueError("session calendar version is required")
    if not symbol_map.get("version"):
        raise ValueError("symbol map version is required")
    if not normalization_policy.get("version"):
        raise ValueError("normalization policy version is required")

    calendar_ids = set(calendars["calendars"])
    canonical_symbols = {symbol["canonical_symbol"] for symbol in symbol_map["symbols"]}
    approved_sources = []

    for source in inventory["sources"]:
        if not source.get("owner"):
            raise ValueError(f"owner is required for source {source['source_id']}")
        if source["source_status"] == "APPROVED_FIXTURE":
            approved_sources.append(source)
            if source["session_calendar_id"] not in calendar_ids:
                raise ValueError(f"unknown session calendar: {source['session_calendar_id']}")
            if source["canonical_symbol"] not in canonical_symbols:
                raise ValueError(f"unknown canonical symbol: {source['canonical_symbol']}")
        elif source["source_id"].startswith("real-") and source["source_status"] != "OPEN_HUMAN_DECISION":
            raise ValueError(f"real source is not human-approved: {source['source_id']}")

    if len(approved_sources) != 1:
        raise ValueError("exactly one approved fixture source is required in Phase 1")


def validate_raw_source_manifest() -> None:
    inventory = load_yaml("configs/data/source-inventory.yaml")
    fixture_source = next(source for source in inventory["sources"] if source["source_status"] == "APPROVED_FIXTURE")
    raw_path = ROOT / fixture_source["raw_file"]
    rows = read_csv_rows(raw_path)
    payload = {
        "manifest_version": "raw-source-manifest-0.1.0",
        "source_id": fixture_source["source_id"],
        "source_type": fixture_source["source_type"],
        "source_status": fixture_source["source_status"],
        "asset_class": fixture_source["asset_class"],
        "venue": fixture_source["venue"],
        "canonical_symbol": fixture_source["canonical_symbol"],
        "raw_symbol": fixture_source["raw_symbol"],
        "timeframe": fixture_source["timeframe"],
        "timezone": fixture_source["timezone"],
        "session_calendar_id": fixture_source["session_calendar_id"],
        "schema_version": fixture_source["schema_version"],
        "raw_file": fixture_source["raw_file"],
        "raw_file_sha256": sha256_file(raw_path),
        "row_count": len(rows),
        "first_observed_at": "2026-08-28T13:30:00Z",
        "last_observed_at": "2026-08-28T13:35:00Z",
        "ingested_at": "2026-08-31T00:00:00Z",
        "correction_policy": fixture_source["correction_policy"],
        "owner": fixture_source["owner"],
    }
    validate_json_payload(ROOT / "schemas/raw_source_manifest.schema.json", payload)


def validate_fixture_replay() -> None:
    inventory = load_yaml("configs/data/source-inventory.yaml")
    fixture_source = next(source for source in inventory["sources"] if source["source_status"] == "APPROVED_FIXTURE")
    raw_path = ROOT / fixture_source["raw_file"]
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    records = [
        normalize_ohlcv_row(
            row,
            policy,
            symbol_map,
            source_id=fixture_source["source_id"],
            source_version=fixture_source["schema_version"],
        )
        for row in read_csv_rows(raw_path)
    ]
    build_availability_intervals(sorted(records, key=lambda record: record.observed_at))

    manifest = build_phase1_dataset_payload(ROOT)
    validate_json_payload(ROOT / "schemas/dataset_manifest.schema.json", manifest)
    expected = json.loads(
        (ROOT / "tests/fixtures/data_foundation/expected/phase1_dataset_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if manifest != expected:
        raise ValueError("Phase 1 replay manifest differs from expected fixture")


def main() -> None:
    validate_schema_file("schemas/raw_source_manifest.schema.json")
    validate_schema_file("schemas/dataset_manifest.schema.json")
    validate_data_configs()
    validate_raw_source_manifest()
    validate_fixture_replay()
    print("Phase 1 artifacts validated")


if __name__ == "__main__":
    main()

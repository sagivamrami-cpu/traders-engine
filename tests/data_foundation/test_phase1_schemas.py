import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def assert_valid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def assert_invalid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert errors


def raw_source_manifest_payload() -> dict:
    return {
        "manifest_version": "raw-source-manifest-0.1.0",
        "source_id": "ohlcv-fixture-v1",
        "source_type": "OHLCV_BAR",
        "source_status": "APPROVED_FIXTURE",
        "asset_class": "EQUITY_ETF",
        "venue": "TEST_FIXTURE",
        "canonical_symbol": "TR_FIXTURE_SPY",
        "raw_symbol": "SPY",
        "timeframe": "1m",
        "timezone": "America/New_York",
        "session_calendar_id": "us-equities-regular-v1",
        "schema_version": "ohlcv-fixture-schema-0.1.0",
        "raw_file": "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv",
        "raw_file_sha256": "a" * 64,
        "row_count": 6,
        "first_observed_at": "2026-08-28T13:30:00Z",
        "last_observed_at": "2026-08-28T13:35:00Z",
        "ingested_at": "2026-08-31T00:00:00Z",
        "correction_policy": "corrections_preserve_available_at",
        "owner": "Codex Architecture Lead",
    }


def dataset_manifest_payload() -> dict:
    return {
        "dataset_id": "phase1-fixture-dataset",
        "dataset_version": "phase1-fixture-dataset-0.1.0",
        "created_at": "2026-08-31T00:00:00Z",
        "phase": 1,
        "source_hashes": {"ohlcv-fixture-v1": "b" * 64},
        "normalization_policy_version": "normalization-policy-0.1.0",
        "session_calendar_version": "session-calendar-0.1.0",
        "symbol_map_version": "symbol-map-0.1.0",
        "date_ranges": {
            "ohlcv-fixture-v1": {
                "first_observed_at": "2026-08-28T13:30:00Z",
                "last_observed_at": "2026-08-28T13:35:00Z",
            }
        },
        "record_count": 6,
        "availability_summary": {
            "interval_count": 5,
            "first_available_at": "2026-08-28T13:30:05Z",
            "last_available_at": "2026-08-28T13:36:30Z",
        },
        "quality_status_counts": {
            "VALID": 2,
            "MISSING": 1,
            "STALE": 1,
            "CORRECTED": 1,
            "INVALID": 1,
            "UNKNOWN": 0,
        },
        "replay_fingerprint": "c" * 64,
    }


def test_raw_source_manifest_schema_accepts_complete_payload():
    assert_valid("raw_source_manifest.schema.json", raw_source_manifest_payload())


def test_raw_source_manifest_rejects_missing_hash():
    payload = raw_source_manifest_payload()
    del payload["raw_file_sha256"]
    assert_invalid("raw_source_manifest.schema.json", payload)


def test_raw_source_manifest_rejects_unsupported_status():
    payload = raw_source_manifest_payload()
    payload["source_status"] = "APPROVED_REAL"
    assert_invalid("raw_source_manifest.schema.json", payload)


def test_dataset_manifest_schema_accepts_complete_payload():
    assert_valid("dataset_manifest.schema.json", dataset_manifest_payload())


def test_dataset_manifest_rejects_missing_replay_fingerprint():
    payload = dataset_manifest_payload()
    del payload["replay_fingerprint"]
    assert_invalid("dataset_manifest.schema.json", payload)


def test_dataset_manifest_rejects_non_phase_one_payload():
    payload = dataset_manifest_payload()
    payload["phase"] = 2
    assert_invalid("dataset_manifest.schema.json", payload)

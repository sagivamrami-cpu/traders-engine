import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.csv_onboarding import (
    CsvOnboardingError,
    build_raw_source_manifest_for_csv,
)
from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def metadata() -> dict:
    return yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))


def validate_manifest(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/raw_source_manifest.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def build_manifest(csv_path: Path = FIXTURE_CSV) -> dict:
    return build_raw_source_manifest_for_csv(
        csv_path,
        metadata(),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def test_fixture_csv_onboarding_emits_valid_raw_source_manifest():
    manifest = build_manifest()

    validate_manifest(manifest)
    assert manifest["source_id"] == "local-csv-ohlcv-fixture"
    assert manifest["source_status"] == "OPEN_HUMAN_DECISION"


def test_manifest_hash_row_count_and_date_range_are_deterministic():
    manifest = build_manifest()

    assert manifest["raw_file_sha256"] == sha256_file(FIXTURE_CSV)
    assert manifest["row_count"] == 6
    assert manifest["first_observed_at"] == "2026-08-28T13:30:00Z"
    assert manifest["last_observed_at"] == "2026-08-28T13:35:00Z"


def test_missing_required_columns_fail_explicitly(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("raw_symbol,timestamp,open\nSPY,2026-08-28T09:30:00,450\n", encoding="utf-8")

    with pytest.raises(CsvOnboardingError, match="missing required columns"):
        build_manifest(csv_path)


def test_unknown_symbols_fail_explicitly(tmp_path: Path):
    csv_path = tmp_path / "unknown.csv"
    csv_path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace("SPY,", "UNKNOWN,", 1),
        encoding="utf-8",
    )

    with pytest.raises(CsvOnboardingError, match="Unknown raw symbol"):
        build_manifest(csv_path)


def test_onboarding_rejects_real_metadata_with_fixture_canonical_symbol():
    bad_metadata = metadata()
    bad_metadata["source_id"] = "real-ohlcv-spy-1m"
    bad_metadata["canonical_symbol"] = "TR_FIXTURE_SPY"

    with pytest.raises(CsvOnboardingError, match="FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE"):
        build_raw_source_manifest_for_csv(
            FIXTURE_CSV,
            bad_metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        )

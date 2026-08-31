import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.normalization import load_normalization_policy

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def metadata_inputs() -> dict:
    return {
        "source_id": "local-csv-ohlcv-spy",
        "canonical_symbol": "TR_REAL_SPY",
        "asset_class": "EQUITY_ETF",
        "venue": "LOCAL_CSV",
        "timeframe": "1m",
        "session_calendar_id": "us-equities-regular-v1",
        "owner": "Human Data Owner",
    }


def inspect(csv_path: Path = FIXTURE_CSV):
    return inspect_local_ohlcv_csv(
        csv_path,
        metadata_inputs(),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/local_csv_inspection_report.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_fixture_csv_inspection_payload_validates_against_schema():
    payload = inspect().to_payload()

    validate_payload(payload)
    assert payload["inspection_version"] == "local-csv-inspection-report-0.1.0"
    assert payload["mode"] == "LOCAL_OHLCV_CSV_INSPECTION"


def test_fixture_csv_is_ready_for_bundle_validation():
    payload = inspect().to_payload()

    assert payload["status"] == "READY_FOR_BUNDLE_VALIDATION"
    assert payload["raw_file_sha256"] == sha256_file(FIXTURE_CSV)
    assert payload["row_count"] == 6
    assert payload["raw_symbols"] == ["SPY"]
    assert payload["first_observed_at"] == "2026-08-28T13:30:00Z"
    assert payload["last_observed_at"] == "2026-08-28T13:35:00Z"


def test_fixture_csv_suggests_unapproved_metadata():
    suggested = inspect().to_payload()["suggested_metadata"]

    assert suggested["source_id"] == "local-csv-ohlcv-spy"
    assert suggested["source_status"] == "OPEN_HUMAN_DECISION"
    assert suggested["raw_symbol"] == "SPY"
    assert suggested["canonical_symbol"] == "TR_REAL_SPY"


def test_missing_columns_block_inspection(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("raw_symbol,timestamp,open\nSPY,2026-08-28T09:30:00,450\n", encoding="utf-8")

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "MISSING_REQUIRED_COLUMNS" in payload["blocked_reasons"]
    assert "available_at" in payload["missing_columns"]
    assert payload["suggested_metadata"] is None


def test_multi_symbol_csv_blocks_metadata_suggestion(tmp_path: Path):
    csv_path = tmp_path / "multi.csv"
    csv_path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace("SPY,", "QQQ,", 1),
        encoding="utf-8",
    )

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert payload["raw_symbols"] == ["QQQ", "SPY"]
    assert "MULTIPLE_RAW_SYMBOLS_REQUIRE_SPLIT" in payload["blocked_reasons"]
    assert payload["suggested_metadata"] is None

import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def metadata_inputs() -> dict:
    return {
        "source_id": "local-csv-ohlcv-spy",
        "canonical_symbol": "TR_FIXTURE_SPY",
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
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def valid_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace(
            "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
        ),
        encoding="utf-8",
    )
    return csv_path


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/local_csv_inspection_report.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_fixture_csv_inspection_payload_validates_against_schema():
    payload = inspect().to_payload()

    validate_payload(payload)
    assert payload["inspection_version"] == "local-csv-inspection-report-0.2.0"
    assert payload["mode"] == "LOCAL_OHLCV_CSV_INSPECTION"


def test_valid_csv_shape_needs_bundle_validation(tmp_path: Path):
    csv_path = valid_csv(tmp_path)
    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "SHAPE_VALIDATED_NEEDS_BUNDLE_VALIDATION"
    assert payload["raw_file_sha256"] == sha256_file(csv_path)
    assert payload["row_count"] == 6
    assert payload["raw_symbols"] == ["SPY"]
    assert payload["first_observed_at"] == "2026-08-28T13:30:00Z"
    assert payload["last_observed_at"] == "2026-08-28T13:35:00Z"


def test_valid_csv_suggests_unapproved_metadata(tmp_path: Path):
    suggested = inspect(valid_csv(tmp_path)).to_payload()["suggested_metadata"]

    assert suggested["source_id"] == "local-csv-ohlcv-spy"
    assert suggested["source_status"] == "OPEN_HUMAN_DECISION"
    assert suggested["raw_symbol"] == "SPY"
    assert suggested["canonical_symbol"] == "TR_FIXTURE_SPY"


def test_canonical_symbol_mismatch_blocks_inspection():
    inputs = metadata_inputs()
    inputs["canonical_symbol"] = "TR_REAL_SPY"

    payload = inspect_local_ohlcv_csv(
        FIXTURE_CSV,
        inputs,
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "CANONICAL_SYMBOL_MISMATCH" in payload["blocked_reasons"]
    assert payload["suggested_metadata"] is None


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


def test_blank_raw_symbol_blocks_inspection(tmp_path: Path):
    csv_path = tmp_path / "blank-symbol.csv"
    csv_path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace("SPY,", ",", 1), encoding="utf-8")

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "RAW_SYMBOL_REQUIRED" in payload["blocked_reasons"]
    assert payload["suggested_metadata"] is None


def test_unknown_raw_symbol_blocks_inspection(tmp_path: Path):
    csv_path = tmp_path / "unknown-symbol.csv"
    csv_path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace("SPY,", "QQQ,", 1), encoding="utf-8")

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "UNKNOWN_RAW_SYMBOL" in payload["blocked_reasons"]
    assert payload["suggested_metadata"] is None


def test_invalid_ohlc_blocks_inspection(tmp_path: Path):
    csv_path = tmp_path / "invalid-ohlc.csv"
    csv_path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace(",451.0,449.5,", ",449.0,451.0,", 1), encoding="utf-8")

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "INVALID_OHLC" in payload["blocked_reasons"]


def test_duplicate_timestamp_blocks_inspection(tmp_path: Path):
    rows = FIXTURE_CSV.read_text(encoding="utf-8").splitlines()
    rows[2] = rows[1]
    csv_path = tmp_path / "duplicate.csv"
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "DUPLICATE_TIMESTAMPS" in payload["blocked_reasons"]


def test_available_before_observed_blocks_inspection(tmp_path: Path):
    csv_path = tmp_path / "lookahead-clock.csv"
    csv_path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace(
            "2026-08-28T09:30:02,SPY",
            "2026-08-28T09:29:59,SPY",
            1,
        ).replace(
            "2026-08-28T09:30:05",
            "2026-08-28T09:29:59",
            1,
        ),
        encoding="utf-8",
    )

    payload = inspect(csv_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "AVAILABLE_AT_BEFORE_OBSERVED_AT" in payload["blocked_reasons"]

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_system.data_foundation.contracts import CorrectionStatus, QualityStatus
from trading_system.data_foundation.normalization import (
    UnknownSymbolError,
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_FIXTURE = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def normalize_row(index: int):
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    rows = read_csv_rows(RAW_FIXTURE)
    return normalize_ohlcv_row(
        rows[index],
        policy,
        symbol_map,
        source_id="ohlcv-fixture-v1",
        source_version="ohlcv-fixture-schema-0.1.0",
    )


def test_raw_symbol_maps_to_canonical_symbol():
    record = normalize_row(0)

    assert record.raw_symbol == "SPY"
    assert record.canonical_symbol == "TR_FIXTURE_SPY"


def test_timestamps_are_converted_to_utc():
    record = normalize_row(0)

    assert record.observed_at == datetime(2026, 8, 28, 13, 30, tzinfo=UTC)
    assert record.available_at == datetime(2026, 8, 28, 13, 30, 5, tzinfo=UTC)


def test_unknown_symbol_is_rejected():
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    row = dict(read_csv_rows(RAW_FIXTURE)[0])
    row["raw_symbol"] = "UNKNOWN"

    with pytest.raises(UnknownSymbolError):
        normalize_ohlcv_row(
            row,
            policy,
            symbol_map,
            source_id="ohlcv-fixture-v1",
            source_version="ohlcv-fixture-schema-0.1.0",
        )


def test_missing_volume_remains_distinct_from_zero():
    record = normalize_row(2)

    assert record.volume is None
    assert record.quality_status is QualityStatus.MISSING
    assert "MISSING_VOLUME" in record.reason_codes


def test_delayed_availability_becomes_stale():
    record = normalize_row(3)

    assert record.quality_status is QualityStatus.STALE
    assert "AVAILABLE_AFTER_STALE_THRESHOLD" in record.reason_codes


def test_corrected_row_preserves_correction_status():
    record = normalize_row(4)

    assert record.correction_status is CorrectionStatus.CORRECTED
    assert record.quality_status is QualityStatus.CORRECTED


def test_invalid_ohlc_is_invalid():
    record = normalize_row(5)

    assert record.quality_status is QualityStatus.INVALID
    assert "HIGH_BELOW_LOW" in record.reason_codes

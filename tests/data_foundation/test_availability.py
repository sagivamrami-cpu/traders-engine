from pathlib import Path

import pytest

from trading_system.data_foundation.availability import build_availability_intervals
from trading_system.data_foundation.contracts import QualityStatus
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)

ROOT = Path(__file__).resolve().parents[2]


def normalized_records():
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    return [
        normalize_ohlcv_row(
            row,
            policy,
            symbol_map,
            source_id="ohlcv-fixture-v1",
            source_version="ohlcv-fixture-schema-0.1.0",
        )
        for row in read_csv_rows(ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv")
    ]


def test_availability_intervals_split_on_quality_status():
    intervals = build_availability_intervals(normalized_records())

    assert [interval.quality_status for interval in intervals] == [
        QualityStatus.VALID,
        QualityStatus.MISSING,
        QualityStatus.STALE,
        QualityStatus.CORRECTED,
        QualityStatus.INVALID,
    ]
    assert intervals[0].record_count == 2
    assert intervals[2].reason_codes == ("AVAILABLE_AFTER_STALE_THRESHOLD",)


def test_availability_rejects_decreasing_observation_times():
    records = normalized_records()

    with pytest.raises(ValueError, match="sorted"):
        build_availability_intervals([records[1], records[0]])

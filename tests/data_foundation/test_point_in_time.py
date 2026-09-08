from datetime import UTC, datetime
from pathlib import Path

from trading_system.data_foundation.contracts import QualityStatus
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.data_foundation.point_in_time import latest_bar_at, records_available_at

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


def test_records_unavailable_at_observation_time_are_excluded():
    records = normalized_records()
    available = records_available_at(records, datetime(2026, 8, 28, 13, 34, tzinfo=UTC))

    observed_minutes = [record.observed_at.minute for record in available]
    assert 33 not in observed_minutes
    assert 34 not in observed_minutes


def test_late_correction_does_not_change_past_view():
    records = normalized_records()
    latest = latest_bar_at(records, "TR_FIXTURE_SPY", datetime(2026, 8, 28, 13, 34, 30, tzinfo=UTC))

    assert latest is not None
    assert latest.observed_at == datetime(2026, 8, 28, 13, 32, tzinfo=UTC)


def test_missing_status_is_not_converted_to_zero():
    records = normalized_records()
    available = records_available_at(records, datetime(2026, 8, 28, 13, 33, tzinfo=UTC))
    missing = [record for record in available if record.quality_status is QualityStatus.MISSING]

    assert missing
    assert missing[0].volume is None


def test_output_ordering_is_stable():
    records = list(reversed(normalized_records()))
    available = records_available_at(records, datetime(2026, 8, 28, 13, 40, tzinfo=UTC))

    assert available == sorted(available, key=lambda record: (record.observed_at, record.source_id, record.raw_symbol))

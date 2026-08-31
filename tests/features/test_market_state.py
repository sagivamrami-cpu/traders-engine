import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.features.market_state import build_unified_market_state

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


def validate_ums(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/unified_market_state.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_market_state_uses_latest_record_available_at_observation_time():
    snapshot = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )

    assert snapshot.feature_values["data.observed_at"].value == "2026-08-28T13:32:00Z"
    assert snapshot.data_quality == "DEGRADED"


def test_market_state_excludes_delayed_records_until_available_at():
    before_stale_available = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 35, 30, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 35, 31, tzinfo=UTC),
    )
    after_stale_available = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 36, 30, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 36, 31, tzinfo=UTC),
    )

    assert before_stale_available.feature_values["data.observed_at"].value == "2026-08-28T13:35:00Z"
    assert after_stale_available.feature_values["data.observed_at"].value == "2026-08-28T13:35:00Z"


def test_market_state_snapshot_id_is_deterministic():
    first = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    second = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )

    assert first.snapshot_id == second.snapshot_id


def test_market_state_payload_validates_against_schema():
    snapshot = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )

    validate_ums(snapshot.to_payload())
    assert snapshot.data_quality == "VALID"

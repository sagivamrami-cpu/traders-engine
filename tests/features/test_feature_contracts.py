import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.features.contracts import FeatureValue, UnifiedMarketState

ROOT = Path(__file__).resolve().parents[2]


def validate(schema_name: str, payload: dict) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_feature_value_payload_matches_phase0_schema():
    feature = FeatureValue(
        name="data.symbol",
        value="TR_FIXTURE_SPY",
        dtype="string",
        status="VALID",
        observed_at=datetime(2026, 8, 28, 13, 30, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 30, 5, tzinfo=UTC),
        source="price-action-fixture-engine",
        engine_version="price-action-engine-0.1.0",
        confidence=1.0,
    )

    payload = feature.to_payload()

    validate("feature_value.schema.json", payload)
    assert payload["observed_at"] == "2026-08-28T13:30:00Z"


def test_unified_market_state_payload_matches_phase0_schema():
    feature = FeatureValue(
        name="data.closed_bar",
        value=True,
        dtype="boolean",
        status="VALID",
        observed_at=datetime(2026, 8, 28, 13, 30, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 30, 5, tzinfo=UTC),
        source="price-action-fixture-engine",
        engine_version="price-action-engine-0.1.0",
        confidence=1.0,
    )
    snapshot = UnifiedMarketState(
        snapshot_id="snapshot-1",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 30, tzinfo=UTC),
        schema_version="unified-market-state-0.1.0",
        data_quality="VALID",
        feature_values={"data.closed_bar": feature},
        availability={"ohlcv-fixture-v1": True},
        regime={"primary": "FIXTURE_NEUTRAL", "probabilities": {"FIXTURE_NEUTRAL": 1.0}},
    )

    payload = snapshot.to_payload()

    validate("unified_market_state.schema.json", payload)
    assert payload["feature_values"]["data.closed_bar"]["value"] is True

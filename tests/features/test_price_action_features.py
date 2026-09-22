import yaml
from datetime import UTC, datetime
from pathlib import Path

from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.features.price_action import compute_price_action_features
from trading_system.features.registry import load_feature_engine_registry

ROOT = Path(__file__).resolve().parents[2]
RAW_FIXTURE = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


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
        for row in read_csv_rows(RAW_FIXTURE)
    ]


def by_name(features):
    return {feature.name: feature for feature in features}


def test_feature_engine_registry_matches_catalog():
    registry = load_feature_engine_registry(ROOT / "configs/features/feature-engine-registry.yaml")
    catalog = yaml.safe_load((ROOT / "configs/features/feature-catalog.yaml").read_text(encoding="utf-8"))
    catalog_ids = {
        feature["id"]
        for family in catalog["feature_families"]
        for feature in family["features"]
    }

    assert registry.version == "feature-engine-registry-0.1.0"
    assert registry.engines["price.action"].engine_version == "price-action-engine-0.1.0"
    assert set(registry.engines["data.provenance"].feature_ids).issubset(catalog_ids)


def test_price_action_features_include_data_provenance_and_closed_bar():
    records = normalized_records()
    features = by_name(
        compute_price_action_features(
            records[1],
            records[0],
            computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        )
    )

    assert features["data.symbol"].value == "TR_FIXTURE_SPY"
    assert features["data.closed_bar"].value is True
    assert features["data.freshness_status"].value == "VALID"


def test_price_action_features_compute_close_to_close_return_and_bar_shape():
    records = normalized_records()
    features = by_name(
        compute_price_action_features(
            records[1],
            records[0],
            computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        )
    )

    assert features["price.return_pct"].value == 0.0011098779134295228
    assert features["price.range_pct"].value == 0.0022172949002217295
    assert features["price.body_pct"].value == 0.0011086474501108647


def test_unavailable_previous_bar_makes_return_unavailable():
    records = normalized_records()
    features = by_name(
        compute_price_action_features(
            records[0],
            None,
            computed_at=datetime(2026, 8, 28, 13, 30, 5, tzinfo=UTC),
        )
    )

    assert features["price.return_pct"].status == "UNAVAILABLE"
    assert features["price.return_pct"].value is None


def test_source_quality_status_is_preserved_without_zero_coercion():
    records = normalized_records()
    missing_features = by_name(
        compute_price_action_features(
            records[2],
            records[1],
            computed_at=datetime(2026, 8, 28, 13, 32, 5, tzinfo=UTC),
        )
    )
    stale_features = by_name(
        compute_price_action_features(
            records[3],
            records[2],
            computed_at=datetime(2026, 8, 28, 13, 36, 30, tzinfo=UTC),
        )
    )
    invalid_features = by_name(
        compute_price_action_features(
            records[5],
            records[4],
            computed_at=datetime(2026, 8, 28, 13, 35, 5, tzinfo=UTC),
        )
    )

    assert missing_features["data.freshness_status"].status == "MISSING"
    assert missing_features["data.freshness_status"].value == "MISSING"
    assert stale_features["data.freshness_status"].status == "STALE"
    assert invalid_features["data.freshness_status"].status == "UNAVAILABLE"

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.normalization import (  # noqa: E402
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.features.market_state import build_unified_market_state  # noqa: E402
from trading_system.features.registry import load_feature_engine_registry  # noqa: E402


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def load_yaml(relative_path: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def validate_payload(schema_name: str, payload: dict[str, Any]) -> None:
    schema = load_json(f"schemas/{schema_name}")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def catalog_feature_ids() -> set[str]:
    catalog = load_yaml("configs/features/feature-catalog.yaml")
    return {
        feature["id"]
        for family in catalog["feature_families"]
        for feature in family["features"]
    }


def validate_registry() -> None:
    registry = load_feature_engine_registry(ROOT / "configs/features/feature-engine-registry.yaml")
    if not registry.version:
        raise ValueError("feature engine registry version is required")
    known_feature_ids = catalog_feature_ids()
    for engine in registry.engines.values():
        if not engine.deterministic:
            raise ValueError(f"engine must be deterministic: {engine.engine_id}")
        if not engine.engine_version:
            raise ValueError(f"engine version is required: {engine.engine_id}")
        unknown = set(engine.feature_ids) - known_feature_ids
        if unknown:
            raise ValueError(f"unknown feature ids for {engine.engine_id}: {sorted(unknown)}")


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


def validate_market_state_snapshots() -> None:
    records = normalized_records()
    first = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    second = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, 0, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    repeated_first = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )

    if first.to_payload() != repeated_first.to_payload():
        raise ValueError("Phase 2 market state replay is not stable")

    for snapshot in [first, second]:
        payload = snapshot.to_payload()
        validate_payload("unified_market_state.schema.json", payload)
        for feature_payload in payload["feature_values"].values():
            validate_payload("feature_value.schema.json", feature_payload)


def main() -> None:
    validate_registry()
    validate_market_state_snapshots()
    print("Phase 2 artifacts validated")


if __name__ == "__main__":
    main()

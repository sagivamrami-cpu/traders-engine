from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.candidates.generation import generate_fixture_candidate  # noqa: E402
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate  # noqa: E402
from trading_system.data_foundation.normalization import (  # noqa: E402
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.features.market_state import build_unified_market_state  # noqa: E402


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def validate_payload(schema_name: str, payload: dict[str, Any]) -> None:
    schema = load_json(f"schemas/{schema_name}")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


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


def main() -> None:
    records = normalized_records()
    valid_snapshot = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    degraded_snapshot = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    eligible = generate_fixture_candidate(
        valid_snapshot,
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    rejected = generate_fixture_candidate(
        degraded_snapshot,
        created_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    contract = build_fixture_trade_contract(records[1])
    label = label_long_candidate(eligible, contract, records[2:4])

    if eligible.status != "ELIGIBLE":
        raise ValueError("expected eligible fixture candidate")
    if rejected.status != "REJECTED":
        raise ValueError("expected rejected fixture candidate")

    validate_payload("candidate_action.schema.json", eligible.to_payload())
    validate_payload("candidate_action.schema.json", rejected.to_payload())
    validate_payload("trade_contract.schema.json", contract.to_payload())
    validate_payload("outcome_label.schema.json", label.to_payload())
    print("Phase 3 artifacts validated")


if __name__ == "__main__":
    main()

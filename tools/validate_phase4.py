from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.candidates.generation import generate_fixture_candidate  # noqa: E402
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate  # noqa: E402
from trading_system.data_foundation.hashing import sha256_file  # noqa: E402
from trading_system.data_foundation.normalization import (  # noqa: E402
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.datasets.factory import build_candidate_training_row  # noqa: E402
from trading_system.features.market_state import build_unified_market_state  # noqa: E402


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def validate_row(payload: dict[str, Any]) -> None:
    schema = load_json("schemas/candidate_training_row.schema.json")
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
    source_hashes = {
        "ohlcv-fixture-v1": sha256_file(ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv")
    }
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
    high_quality_label = label_long_candidate(
        eligible,
        contract,
        [replace(records[2], high=452.7, low=450.9, close=452.6)],
    )
    ambiguous_label = label_long_candidate(
        eligible,
        contract,
        [replace(records[2], high=452.7, low=450.1, close=451.0)],
    )
    rows = [
        build_candidate_training_row(
            valid_snapshot,
            eligible,
            contract,
            high_quality_label,
            split="TRAIN",
            source_hashes=source_hashes,
        ),
        build_candidate_training_row(
            degraded_snapshot,
            rejected,
            None,
            None,
            split="VALIDATION",
            source_hashes=source_hashes,
        ),
        build_candidate_training_row(
            valid_snapshot,
            eligible,
            contract,
            ambiguous_label,
            split="TRAIN",
            source_hashes=source_hashes,
        ),
    ]

    if not rows[0].included_in_training:
        raise ValueError("expected first fixture row to be included")
    if rows[1].included_in_training or rows[2].included_in_training:
        raise ValueError("expected rejected and ambiguous rows to be excluded")
    if rows[0].row_id != build_candidate_training_row(
        valid_snapshot,
        eligible,
        contract,
        high_quality_label,
        split="TRAIN",
        source_hashes=source_hashes,
    ).row_id:
        raise ValueError("dataset row id is not deterministic")
    for row in rows:
        validate_row(row.to_payload())
    print("Phase 4 artifacts validated")


if __name__ == "__main__":
    main()

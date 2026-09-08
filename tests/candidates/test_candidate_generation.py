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
from trading_system.candidates.generation import generate_fixture_candidate

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


def validate_candidate(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/candidate_action.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def valid_snapshot():
    return build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )


def degraded_snapshot():
    return build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, 0, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )


def test_valid_positive_return_snapshot_emits_eligible_long():
    candidate = generate_fixture_candidate(
        valid_snapshot(),
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )

    assert candidate.status == "ELIGIBLE"
    assert candidate.direction == "LONG"
    assert "POSITIVE_RETURN" in candidate.reasons
    validate_candidate(candidate.to_payload())


def test_degraded_snapshot_emits_rejected_candidate_with_reason():
    candidate = generate_fixture_candidate(
        degraded_snapshot(),
        created_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )

    assert candidate.status == "REJECTED"
    assert "DATA_QUALITY_DEGRADED" in candidate.reasons
    validate_candidate(candidate.to_payload())


def test_candidate_id_is_deterministic():
    first = generate_fixture_candidate(
        valid_snapshot(),
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    second = generate_fixture_candidate(
        valid_snapshot(),
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )

    assert first.candidate_id == second.candidate_id

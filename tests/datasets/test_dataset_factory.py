import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.candidates.generation import generate_fixture_candidate
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.datasets.factory import build_candidate_training_row
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


def validate_row(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/candidate_training_row.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def included_fixture_row():
    records = normalized_records()
    snapshot = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    candidate = generate_fixture_candidate(
        snapshot,
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    contract = build_fixture_trade_contract(records[1])
    future = [replace(records[2], high=452.7, low=450.9, close=452.6)]
    label = label_long_candidate(candidate, contract, future)
    return build_candidate_training_row(
        snapshot,
        candidate,
        contract,
        label,
        split="TRAIN",
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )


def test_eligible_high_quality_label_is_included_in_training():
    row = included_fixture_row()

    assert row.included_in_training is True
    assert row.outcome_class == "TARGET_FIRST"
    validate_row(row.to_payload())


def test_row_id_is_deterministic():
    assert included_fixture_row().row_id == included_fixture_row().row_id


def test_rejected_candidate_is_kept_but_excluded():
    records = normalized_records()
    snapshot = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    candidate = generate_fixture_candidate(
        snapshot,
        created_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    row = build_candidate_training_row(
        snapshot,
        candidate,
        None,
        None,
        split="VALIDATION",
        source_hashes={"ohlcv-fixture-v1": "b" * 64},
    )

    assert row.candidate_status == "REJECTED"
    assert row.included_in_training is False
    assert "CANDIDATE_REJECTED" in row.exclusion_reasons
    validate_row(row.to_payload())


def test_ambiguous_label_is_kept_but_excluded():
    records = normalized_records()
    snapshot = build_unified_market_state(
        records,
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    candidate = generate_fixture_candidate(
        snapshot,
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    contract = build_fixture_trade_contract(records[1])
    future = [replace(records[2], high=452.7, low=450.1, close=451.0)]
    label = label_long_candidate(candidate, contract, future)
    row = build_candidate_training_row(
        snapshot,
        candidate,
        contract,
        label,
        split="TRAIN",
        source_hashes={"ohlcv-fixture-v1": "c" * 64},
    )

    assert row.outcome_class == "AMBIGUOUS"
    assert row.included_in_training is False
    assert "LABEL_EXCLUDED_FROM_TRAINING" in row.exclusion_reasons

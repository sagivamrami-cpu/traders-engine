from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from trading_system.candidates.generation import generate_fixture_candidate
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate
from trading_system.data_foundation.contracts import NormalizedBar, QualityStatus
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


def eligible_candidate():
    snapshot = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )
    return generate_fixture_candidate(
        snapshot,
        created_at=datetime(2026, 8, 28, 13, 31, 5, tzinfo=UTC),
    )


def make_bar(observed_at: datetime, high: float, low: float, close: float) -> NormalizedBar:
    base = normalized_records()[1]
    return replace(
        base,
        observed_at=observed_at,
        available_at=observed_at,
        high=high,
        low=low,
        close=close,
        quality_status=QualityStatus.VALID,
        reason_codes=(),
    )


def test_target_touched_before_stop_emits_target_first():
    candidate_bar = normalized_records()[1]
    contract = build_fixture_trade_contract(candidate_bar)
    label = label_long_candidate(
        eligible_candidate(),
        contract,
        [make_bar(datetime(2026, 8, 28, 13, 32, tzinfo=UTC), high=452.7, low=450.9, close=452.6)],
    )

    assert label.outcome_class == "TARGET_FIRST"
    assert label.target_before_stop == 1
    assert label.label_quality == "HIGH"


def test_stop_touched_before_target_emits_stop_first():
    candidate_bar = normalized_records()[1]
    contract = build_fixture_trade_contract(candidate_bar)
    label = label_long_candidate(
        eligible_candidate(),
        contract,
        [make_bar(datetime(2026, 8, 28, 13, 32, tzinfo=UTC), high=451.2, low=450.1, close=450.2)],
    )

    assert label.outcome_class == "STOP_FIRST"
    assert label.stop_before_target == 1


def test_no_touch_before_max_bars_emits_expired():
    candidate_bar = normalized_records()[1]
    contract = build_fixture_trade_contract(candidate_bar)
    label = label_long_candidate(
        eligible_candidate(),
        contract,
        [
            make_bar(datetime(2026, 8, 28, 13, 32, tzinfo=UTC), high=451.4, low=450.8, close=451.1),
            make_bar(datetime(2026, 8, 28, 13, 33, tzinfo=UTC), high=451.5, low=450.7, close=451.2),
        ],
    )

    assert label.outcome_class == "EXPIRED"
    assert label.expired == 1


def test_same_bar_target_and_stop_emits_ambiguous_excluded_label():
    candidate_bar = normalized_records()[1]
    contract = build_fixture_trade_contract(candidate_bar)
    label = label_long_candidate(
        eligible_candidate(),
        contract,
        [make_bar(datetime(2026, 8, 28, 13, 32, tzinfo=UTC), high=452.7, low=450.1, close=451.0)],
    )

    assert label.outcome_class == "AMBIGUOUS"
    assert label.label_quality == "EXCLUDED_FROM_TRAINING"


def test_rejected_candidate_is_not_filled_and_excluded_from_training():
    snapshot = build_unified_market_state(
        normalized_records(),
        "TR_FIXTURE_SPY",
        datetime(2026, 8, 28, 13, 33, 0, tzinfo=UTC),
        computed_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    rejected = generate_fixture_candidate(
        snapshot,
        created_at=datetime(2026, 8, 28, 13, 33, 1, tzinfo=UTC),
    )
    contract = build_fixture_trade_contract(normalized_records()[2])
    label = label_long_candidate(rejected, contract, [])

    assert label.outcome_class == "EXPIRED"
    assert label.filled is False
    assert label.label_quality == "EXCLUDED_FROM_TRAINING"

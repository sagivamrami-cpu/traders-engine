from dataclasses import replace
from datetime import UTC, datetime

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.readiness import TrainingPolicy, evaluate_training_readiness


def row(row_id: str, outcome_class: str, split: str, *, included: bool = True) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=row_id,
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        snapshot_id=f"snapshot-{row_id}",
        candidate_id=f"candidate-{row_id}",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 31, tzinfo=UTC),
        graph_id="tr-vshape-retest-long",
        graph_version="fixture-graph-rules-0.1.0",
        direction="LONG",
        candidate_status="ELIGIBLE" if included else "REJECTED",
        features={"price.return_pct": 0.001},
        feature_schema_version="feature-catalog-0.1.0",
        contract_version="fixture-tr-contract-0.1.0" if included else None,
        label_version="fixture-outcome-0.1.0" if included else None,
        outcome_class=outcome_class if included else None,
        label_quality="HIGH" if included else "EXCLUDED_FROM_TRAINING",
        included_in_training=included,
        exclusion_reasons=() if included else ("CANDIDATE_REJECTED",),
        split=split,
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )


def policy() -> TrainingPolicy:
    return TrainingPolicy(
        version="baseline-training-policy-0.1.0",
        min_train_rows=2,
        min_validation_rows=1,
        min_classes=2,
    )


def test_excluded_rows_are_ignored():
    result = evaluate_training_readiness(
        [
            row("1", "TARGET_FIRST", "TRAIN", included=False),
            row("2", "STOP_FIRST", "VALIDATION", included=False),
        ],
        policy(),
    )

    assert "INSUFFICIENT_TRAIN_ROWS" in result.blocked_reasons
    assert result.class_distribution == {}


def test_insufficient_train_rows_blocks_training():
    result = evaluate_training_readiness(
        [row("1", "TARGET_FIRST", "TRAIN"), row("2", "STOP_FIRST", "VALIDATION")],
        policy(),
    )

    assert "INSUFFICIENT_TRAIN_ROWS" in result.blocked_reasons


def test_missing_validation_rows_blocks_training():
    result = evaluate_training_readiness(
        [row("1", "TARGET_FIRST", "TRAIN"), row("2", "STOP_FIRST", "TRAIN")],
        policy(),
    )

    assert "MISSING_VALIDATION_ROWS" in result.blocked_reasons


def test_single_class_blocks_training():
    result = evaluate_training_readiness(
        [
            row("1", "TARGET_FIRST", "TRAIN"),
            row("2", "TARGET_FIRST", "TRAIN"),
            row("3", "TARGET_FIRST", "VALIDATION"),
        ],
        policy(),
    )

    assert "INSUFFICIENT_OUTCOME_CLASSES" in result.blocked_reasons


def test_two_classes_with_train_and_validation_rows_pass_readiness():
    result = evaluate_training_readiness(
        [
            row("1", "TARGET_FIRST", "TRAIN"),
            row("2", "STOP_FIRST", "TRAIN"),
            row("3", "STOP_FIRST", "VALIDATION"),
        ],
        policy(),
    )

    assert result.ready is True
    assert result.blocked_reasons == ()

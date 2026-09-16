from datetime import UTC, datetime

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.models.baseline import train_majority_baseline
from trading_system.models.readiness import TrainingPolicy


def row(row_id: str, outcome_class: str, split: str) -> CandidateTrainingRow:
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
        candidate_status="ELIGIBLE",
        features={"price.return_pct": 0.001},
        feature_schema_version="feature-catalog-0.1.0",
        contract_version="fixture-tr-contract-0.1.0",
        label_version="fixture-outcome-0.1.0",
        outcome_class=outcome_class,
        label_quality="HIGH",
        included_in_training=True,
        exclusion_reasons=(),
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


def test_fixture_sized_dataset_returns_blocked_run():
    run = train_majority_baseline(
        [row("1", "TARGET_FIRST", "TRAIN")],
        policy(),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert run.status == "BLOCKED"
    assert run.baseline_class is None
    assert run.promotion_allowed is False
    assert "INSUFFICIENT_TRAIN_ROWS" in run.blocked_reasons


def test_trainable_rows_return_trained_majority_baseline():
    run = train_majority_baseline(
        [
            row("1", "STOP_FIRST", "TRAIN"),
            row("2", "TARGET_FIRST", "TRAIN"),
            row("3", "STOP_FIRST", "TRAIN"),
            row("4", "STOP_FIRST", "VALIDATION"),
            row("5", "TARGET_FIRST", "TEST"),
        ],
        policy(),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert run.status == "TRAINED"
    assert run.baseline_class == "STOP_FIRST"
    assert run.metrics["validation_accuracy"] == 1.0
    assert run.metrics["test_accuracy"] == 0.0
    assert run.promotion_allowed is False
    assert run.blocked_reasons == ()

from datetime import UTC, datetime, timedelta

from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.evaluation.walk_forward import (
    WalkForwardPolicy,
    build_expanding_windows,
    evaluate_majority_baseline_walk_forward,
)


def row(index: int, outcome_class: str) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=f"row-{index}",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        snapshot_id=f"snapshot-{index}",
        candidate_id=f"candidate-{index}",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 30, tzinfo=UTC) + timedelta(minutes=index),
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
        split="TRAIN",
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )


def policy() -> WalkForwardPolicy:
    return WalkForwardPolicy(
        version="walk-forward-policy-0.1.0",
        min_train_size=3,
        validation_size=1,
        min_windows=2,
        calibration_bin_count=2,
    )


def test_expanding_windows_are_chronological():
    rows = [row(3, "STOP_FIRST"), row(0, "TARGET_FIRST"), row(2, "STOP_FIRST"), row(1, "TARGET_FIRST")]
    windows = build_expanding_windows(rows, min_train_size=2, validation_size=1)

    assert windows[0].train_row_ids == ("row-0", "row-1")
    assert windows[0].validation_row_ids == ("row-2",)
    assert windows[1].train_row_ids == ("row-0", "row-1", "row-2")
    assert windows[1].validation_row_ids == ("row-3",)


def test_fixture_sized_inputs_produce_blocked_evaluation_report():
    report = evaluate_majority_baseline_walk_forward(
        [row(0, "TARGET_FIRST")],
        policy(),
        training_run_id="run-blocked",
        model_version="majority-class-baseline-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert report.promotion_allowed is False
    assert "INSUFFICIENT_WALK_FORWARD_WINDOWS" in report.promotion_gate["blocked_reasons"]


def test_synthetic_rows_can_be_evaluated_across_two_windows():
    report = evaluate_majority_baseline_walk_forward(
        [
            row(0, "STOP_FIRST"),
            row(1, "TARGET_FIRST"),
            row(2, "STOP_FIRST"),
            row(3, "STOP_FIRST"),
            row(4, "TARGET_FIRST"),
        ],
        policy(),
        training_run_id="run-trained",
        model_version="majority-class-baseline-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert len(report.windows) == 2
    assert report.aggregate_metrics["mean_accuracy"] == 0.5
    assert report.calibration["bin_count"] == 2

import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.models.contracts import ModelTrainingRun

ROOT = Path(__file__).resolve().parents[2]


def validate_run(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/model_training_run.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_blocked_training_run_payload_matches_schema():
    run = ModelTrainingRun(
        run_id="run-1",
        run_version="model-training-run-0.1.0",
        status="BLOCKED",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        model_type="MAJORITY_CLASS_BASELINE",
        model_version=None,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        training_policy_version="baseline-training-policy-0.1.0",
        feature_schema_version="feature-catalog-0.1.0",
        label_version="fixture-outcome-0.1.0",
        split_summary={"TRAIN": 1, "VALIDATION": 0, "TEST": 0},
        class_distribution={"TARGET_FIRST": 1},
        baseline_class=None,
        metrics={},
        blocked_reasons=("INSUFFICIENT_TRAIN_ROWS",),
        promotion_allowed=False,
    )

    validate_run(run.to_payload())


def test_trained_training_run_payload_matches_schema():
    run = ModelTrainingRun(
        run_id="run-2",
        run_version="model-training-run-0.1.0",
        status="TRAINED",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        model_type="MAJORITY_CLASS_BASELINE",
        model_version="majority-class-baseline-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        training_policy_version="baseline-training-policy-0.1.0",
        feature_schema_version="feature-catalog-0.1.0",
        label_version="fixture-outcome-0.1.0",
        split_summary={"TRAIN": 3, "VALIDATION": 1, "TEST": 1},
        class_distribution={"TARGET_FIRST": 2, "STOP_FIRST": 3},
        baseline_class="STOP_FIRST",
        metrics={"validation_accuracy": 1.0, "test_accuracy": 0.0},
        blocked_reasons=(),
        promotion_allowed=False,
    )

    validate_run(run.to_payload())

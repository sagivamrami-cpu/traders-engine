import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.evaluation.contracts import ModelEvaluationReport
from trading_system.governance.model_card import build_model_card
from trading_system.models.contracts import ModelTrainingRun

ROOT = Path(__file__).resolve().parents[2]


def validate_card(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/model_card.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def training_run() -> ModelTrainingRun:
    return ModelTrainingRun(
        run_id="run-1",
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
        class_distribution={"STOP_FIRST": 3, "TARGET_FIRST": 2},
        baseline_class="STOP_FIRST",
        metrics={"validation_accuracy": 1.0, "test_accuracy": 0.0},
        blocked_reasons=(),
        promotion_allowed=False,
    )


def evaluation_report() -> ModelEvaluationReport:
    return ModelEvaluationReport(
        report_id="report-1",
        report_version="model-evaluation-report-0.1.0",
        training_run_id="run-1",
        model_version="majority-class-baseline-0.1.0",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 1, tzinfo=UTC),
        evaluation_policy_version="walk-forward-policy-0.1.0",
        windows=[],
        aggregate_metrics={"window_count": 2, "mean_accuracy": 0.5},
        calibration={"ece_target_first": 0.5, "bin_count": 2},
        promotion_gate={
            "promotion_allowed": False,
            "blocked_reasons": [
                "HUMAN_APPROVAL_MISSING",
                "SHADOW_EVIDENCE_MISSING",
                "PAPER_EVIDENCE_MISSING",
                "COST_FILL_EVIDENCE_MISSING",
            ],
        },
        promotion_allowed=False,
    )


def test_model_card_payload_validates_and_remains_blocked():
    card = build_model_card(
        training_run(),
        evaluation_report(),
        created_at=datetime(2026, 8, 31, 0, 2, tzinfo=UTC),
    )

    assert card.approval_status == "BLOCKED"
    assert card.approver is None
    assert card.promotion_allowed is False
    validate_card(card.to_payload())


def test_model_card_preserves_blocked_promotion_reasons():
    card = build_model_card(
        training_run(),
        evaluation_report(),
        created_at=datetime(2026, 8, 31, 0, 2, tzinfo=UTC),
    )

    assert card.blocked_reasons == (
        "HUMAN_APPROVAL_MISSING",
        "SHADOW_EVIDENCE_MISSING",
        "PAPER_EVIDENCE_MISSING",
        "COST_FILL_EVIDENCE_MISSING",
    )
    assert "No live deployment is allowed from this card." in card.known_limitations

import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.evaluation.contracts import EvaluationWindow, ModelEvaluationReport, PredictionPayload

ROOT = Path(__file__).resolve().parents[2]


def validate(schema_name: str, payload: dict) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_prediction_payload_matches_schema():
    prediction = PredictionPayload(
        candidate_id="candidate-1",
        model_id="majority-class-baseline",
        model_version="majority-class-baseline-0.1.0",
        feature_schema_version="feature-catalog-0.1.0",
        p_target_first=1.0,
        p_stop_first=0.0,
        p_expired=0.0,
        expected_net_return_r=2.0,
        expected_mae_r=0.0,
        expected_mfe_r=2.0,
        uncertainty=0.0,
        coverage_status="LOW_COVERAGE",
        calibration_version="uncalibrated-majority-0.1.0",
    )

    validate("prediction.schema.json", prediction.to_payload())


def test_evaluation_report_payload_matches_schema():
    report = ModelEvaluationReport(
        report_id="report-1",
        report_version="model-evaluation-report-0.1.0",
        training_run_id="run-1",
        model_version="majority-class-baseline-0.1.0",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        evaluation_policy_version="walk-forward-policy-0.1.0",
        windows=[
            EvaluationWindow(
                window_id="window-1",
                train_row_ids=("r1", "r2"),
                validation_row_ids=("r3",),
                metrics={"accuracy": 1.0, "brier_target_first": 0.0},
            )
        ],
        aggregate_metrics={"mean_accuracy": 1.0, "mean_brier_target_first": 0.0},
        calibration={"ece_target_first": 0.0, "bin_count": 2},
        promotion_gate={"promotion_allowed": False, "blocked_reasons": ["HUMAN_APPROVAL_MISSING"]},
        promotion_allowed=False,
    )

    validate("model_evaluation_report.schema.json", report.to_payload())

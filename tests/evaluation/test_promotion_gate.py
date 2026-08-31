from datetime import UTC, datetime

from trading_system.evaluation.contracts import ModelEvaluationReport
from trading_system.evaluation.promotion import evaluate_promotion_gate
from trading_system.evaluation.walk_forward import WalkForwardPolicy


def policy() -> WalkForwardPolicy:
    return WalkForwardPolicy(
        version="walk-forward-policy-0.1.0",
        min_train_size=3,
        validation_size=1,
        min_windows=2,
        calibration_bin_count=2,
    )


def report(window_count: int) -> ModelEvaluationReport:
    return ModelEvaluationReport(
        report_id="report-1",
        report_version="model-evaluation-report-0.1.0",
        training_run_id="run-1",
        model_version="majority-class-baseline-0.1.0",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        evaluation_policy_version="walk-forward-policy-0.1.0",
        windows=[],
        aggregate_metrics={"window_count": window_count},
        calibration={"ece_target_first": 0.0, "bin_count": 2},
        promotion_gate={"promotion_allowed": False, "blocked_reasons": []},
        promotion_allowed=False,
    )


def test_promotion_gate_blocks_without_required_evidence():
    gate = evaluate_promotion_gate(report(window_count=2), policy())

    assert gate["promotion_allowed"] is False
    assert gate["blocked_reasons"] == [
        "HUMAN_APPROVAL_MISSING",
        "SHADOW_EVIDENCE_MISSING",
        "PAPER_EVIDENCE_MISSING",
        "COST_FILL_EVIDENCE_MISSING",
    ]


def test_promotion_gate_blocks_insufficient_windows():
    gate = evaluate_promotion_gate(report(window_count=1), policy())

    assert "INSUFFICIENT_WALK_FORWARD_WINDOWS" in gate["blocked_reasons"]

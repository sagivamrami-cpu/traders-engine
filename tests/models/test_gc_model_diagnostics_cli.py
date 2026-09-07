import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BASELINE_RUN = {
    "run_id": "a" * 64,
    "run_version": "model-training-run-0.1.0",
    "status": "TRAINED",
    "dataset_id": "fixture-gc-dataset",
    "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
    "model_type": "MAJORITY_CLASS_BASELINE",
    "model_version": "majority-class-baseline-0.1.0",
    "created_at": "2026-09-07T13:22:35Z",
    "training_policy_version": "baseline-training-policy-0.1.0",
    "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
    "label_version": "gc-outcome-contract-label-0.1.0",
    "split_summary": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
    "class_distribution": {"STOP_FIRST": 4, "TARGET_FIRST": 4},
    "baseline_class": "STOP_FIRST",
    "metrics": {"validation_accuracy": 0.42, "test_accuracy": 0.44},
    "blocked_reasons": [],
    "promotion_allowed": False,
}

FIRST_MODEL_RUN = {
    "run_id": "b" * 64,
    "run_version": "gc-first-real-model-run-0.1.0",
    "status": "TRAINED",
    "dataset_id": "fixture-gc-dataset",
    "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
    "model_type": "REGULARIZED_LOGISTIC_RESEARCH_BASELINE",
    "model_version": "regularized-logistic-research-baseline-0.1.0",
    "created_at": "2026-09-07T14:01:41Z",
    "training_policy_version": "baseline-training-policy-0.1.0",
    "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
    "label_version": "gc-outcome-contract-label-0.1.0",
    "split_summary": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
    "class_distribution": {"STOP_FIRST": 4, "TARGET_FIRST": 4},
    "fit_scope": "TRAIN_ONLY",
    "selection_scope": "VALIDATION_ONLY",
    "final_evaluation_scope": "TEST_ONLY",
    "feature_names": ["ret_1", "of_delta", "direction_is_long"],
    "training_parameters": {"solver": "in_repo_batch_gradient_descent"},
    "selected_threshold": 0.56,
    "threshold_selection_metric": "validation_expected_r_per_candidate",
    "intercept": -0.01,
    "coefficients": {"ret_1": 0.2, "of_delta": -0.5, "direction_is_long": 0.1},
    "metrics": {
        "validation_accuracy": 0.43,
        "test_accuracy": 0.439,
        "validation_expected_r_per_candidate": 0.002,
        "test_expected_r_per_candidate": -0.001,
        "validation_selected_trade_rate": 0.19,
        "test_selected_trade_rate": 0.13,
    },
    "blocked_reasons": [],
    "promotion_allowed": False,
}


def test_gc_model_diagnostics_cli_writes_report(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    first_model_path = tmp_path / "first-model.json"
    report_out = tmp_path / "diagnostics.json"
    baseline_path.write_text(json.dumps(BASELINE_RUN), encoding="utf-8")
    first_model_path.write_text(json.dumps(FIRST_MODEL_RUN), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_model_diagnostics.py",
            "--baseline-run",
            str(baseline_path),
            "--first-model-run",
            str(first_model_path),
            "--report-out",
            str(report_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["promotion_allowed"] is False
    assert payload["status"] == "FEATURE_DIAGNOSTICS_REQUIRED"
    assert "NEGATIVE_TEST_EXPECTED_R" in payload["blocked_reasons"]
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

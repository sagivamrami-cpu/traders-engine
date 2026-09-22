import json
import subprocess
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "first_real_model_cli_fixture",
    ROOT / "tests/models/test_train_gc_first_real_model_cli.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:
    raise RuntimeError("first real model CLI fixture could not be loaded")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
write_tiny_phase46_dataset = _FIXTURE_MODULE.write_tiny_phase46_dataset


def feature_candidates() -> dict:
    return {
        "report_id": "c" * 64,
        "report_version": "gc-normalized-feature-candidates-report-0.1.0",
        "status": "NORMALIZED_FEATURE_CANDIDATES_READY",
        "dataset_id": "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966",
        "variant": "order_flow",
        "research_training_allowed": True,
        "model_promotion_allowed": False,
        "next_model_feature_set": [
            "ret_1",
            "ret_4",
            "ret_8",
            "ret_14",
            "range_over_atr",
            "direction_is_long",
            "direction_is_short",
            "atr_14_over_close",
            "of_delta_over_of_volume",
            "of_delta_sum_14_over_of_volume_sum_14",
            "of_trades_per_minute",
            "of_volume_per_trade",
            "of_volume_vs_14bar_avg",
            "of_trades_vs_14bar_avg",
        ],
        "excluded_raw_features": [
            {"feature": "close", "reason": "RAW_PRICE_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
            {"feature": "atr_14", "reason": "RAW_ATR_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"},
        ],
    }


def previous_model_run() -> dict:
    return {
        "run_id": "d" * 64,
        "metrics": {
            "validation_accuracy": 0.42,
            "test_accuracy": 0.44,
            "validation_expected_r_per_candidate": 0.002,
            "test_expected_r_per_candidate": -0.001,
        },
    }


def baseline_run() -> dict:
    return {
        "run_id": "e" * 64,
        "metrics": {
            "validation_accuracy": 0.41,
            "test_accuracy": 0.43,
        },
    }


def test_train_gc_normalized_feature_model_cli_writes_sanitized_run(tmp_path: Path):
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    candidates_path = tmp_path / "feature-candidates.json"
    previous_path = tmp_path / "previous-model.json"
    baseline_path = tmp_path / "baseline.json"
    run_out = tmp_path / "normalized-run.json"
    candidates_path.write_text(json.dumps(feature_candidates()), encoding="utf-8")
    previous_path.write_text(json.dumps(previous_model_run()), encoding="utf-8")
    baseline_path.write_text(json.dumps(baseline_run()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/train_gc_normalized_feature_model.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
            "--feature-candidates",
            str(candidates_path),
            "--previous-model-run",
            str(previous_path),
            "--baseline-run",
            str(baseline_path),
            "--training-policy",
            "configs/models/baseline-training-policy.yaml",
            "--variant",
            "order_flow",
            "--run-out",
            str(run_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "TRAINED"
    assert payload["model_type"] == "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH"
    assert payload["promotion_allowed"] is False
    assert "close" not in payload["feature_names"]
    assert "atr_14" not in payload["feature_names"]
    assert "atr_14_over_close" in payload["feature_names"]
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(run_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

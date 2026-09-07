import json
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "normalized_feature_model_cli_fixture",
    ROOT / "tests/models/test_train_gc_normalized_feature_model_cli.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:
    raise RuntimeError("normalized feature model CLI fixture could not be loaded")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
feature_candidates = _FIXTURE_MODULE.feature_candidates
write_tiny_phase46_dataset = _FIXTURE_MODULE.write_tiny_phase46_dataset


def model_run() -> dict:
    return {
        "run_id": "d" * 64,
        "run_version": "gc-normalized-feature-model-run-0.1.0",
        "dataset_id": "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966",
        "model_type": "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH",
        "model_version": "normalized-feature-logistic-research-0.1.0",
        "selected_threshold": 0.5,
        "feature_names": feature_candidates()["next_model_feature_set"],
        "intercept": 0.0,
        "coefficients": {name: 0.1 for name in feature_candidates()["next_model_feature_set"]},
        "promotion_allowed": False,
    }


def test_gc_normalized_model_stability_cli_writes_report(tmp_path: Path):
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    candidates_path = tmp_path / "feature-candidates.json"
    model_path = tmp_path / "model-run.json"
    report_out = tmp_path / "stability-report.json"
    candidates_path.write_text(json.dumps(feature_candidates()), encoding="utf-8")
    model_path.write_text(json.dumps(model_run()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_normalized_model_stability.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
            "--feature-candidates",
            str(candidates_path),
            "--model-run",
            str(model_path),
            "--variant",
            "order_flow",
            "--report-out",
            str(report_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "STABILITY_REVIEW_REQUIRED"
    assert payload["promotion_allowed"] is False
    assert payload["evaluation_scope"] == "TEST_ONLY"
    assert payload["monthly_test_segments"]
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def feature_diagnostics() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-feature-diagnostics-report-0.1.0",
        "mode": "GC_FEATURE_DIAGNOSTICS",
        "created_at": "2026-09-07T16:00:00Z",
        "status": "EXPERIMENT_DESIGN_REQUIRED",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "diagnostic_focus": "FEATURE_AND_REGIME_STABILITY",
        "source_model_run_id": "b" * 64,
        "source_model_diagnostics_report_id": "c" * 64,
        "included_rows_by_split": {"TRAIN": 10, "VALIDATION": 5, "TEST": 5},
        "feature_summaries": {
            "close": {"test_drift_z": 8.0},
            "atr_14": {"test_drift_z": 3.5},
        },
        "top_drift_features": [
            {"feature": "close", "test_drift_z": 8.0, "validation_drift_z": 1.8},
            {"feature": "atr_14", "test_drift_z": 3.5, "validation_drift_z": 0.3},
        ],
        "regime_summaries": {},
        "recommended_experiments": ["REGIME_FILTER_RESEARCH"],
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
        "promotion_allowed": False,
    }


def test_gc_normalized_feature_candidates_cli_writes_report(tmp_path: Path):
    diagnostics_path = tmp_path / "feature-diagnostics.json"
    report_out = tmp_path / "normalized-feature-candidates.json"
    diagnostics_path.write_text(json.dumps(feature_diagnostics()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_normalized_feature_candidates.py",
            "--feature-diagnostics",
            str(diagnostics_path),
            "--report-out",
            str(report_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "NORMALIZED_FEATURE_CANDIDATES_READY"
    assert payload["research_training_allowed"] is True
    assert payload["model_promotion_allowed"] is False
    assert "close" not in payload["next_model_feature_set"]
    assert "atr_14" not in payload["next_model_feature_set"]
    assert "atr_14_over_close" in payload["next_model_feature_set"]
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

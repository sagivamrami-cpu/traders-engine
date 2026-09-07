import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "split": "TRAIN",
                "included_order_flow": True,
                "outcome_class": "TARGET_FIRST",
                "direction": "LONG",
                "net_return_r": 1.0,
                "of_delta": 10.0,
                "ret_14": 0.05,
                "atr_14": 2.0,
            },
            {
                "split": "TRAIN",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "SHORT",
                "net_return_r": -1.0,
                "of_delta": -10.0,
                "ret_14": -0.05,
                "atr_14": 6.0,
            },
            {
                "split": "VALIDATION",
                "included_order_flow": True,
                "outcome_class": "TARGET_FIRST",
                "direction": "LONG",
                "net_return_r": 1.0,
                "of_delta": 12.0,
                "ret_14": 0.04,
                "atr_14": 3.0,
            },
            {
                "split": "VALIDATION",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "SHORT",
                "net_return_r": -1.0,
                "of_delta": -12.0,
                "ret_14": -0.04,
                "atr_14": 7.0,
            },
            {
                "split": "TEST",
                "included_order_flow": True,
                "outcome_class": "STOP_FIRST",
                "direction": "LONG",
                "net_return_r": -1.0,
                "of_delta": 100.0,
                "ret_14": 0.03,
                "atr_14": 8.0,
            },
            {
                "split": "TEST",
                "included_order_flow": True,
                "outcome_class": "EXPIRED",
                "direction": "SHORT",
                "net_return_r": -0.2,
                "of_delta": 80.0,
                "ret_14": -0.03,
                "atr_14": 9.0,
            },
        ]
    )


def build_manifest() -> dict:
    return {
        "dataset_id": "fixture-gc-dataset",
        "builder_version": "gc-30m-real-dataset-builder-0.1.0",
        "summary": {
            "variants": {
                "order_flow": {
                    "included_rows_by_split": {"TRAIN": 2, "VALIDATION": 2, "TEST": 2},
                    "included_rows": 6,
                }
            }
        },
    }


def first_model_run() -> dict:
    return {
        "run_id": "a" * 64,
        "dataset_id": "fixture-gc-dataset",
        "model_type": "REGULARIZED_LOGISTIC_RESEARCH_BASELINE",
        "feature_names": ["of_delta", "ret_14", "atr_14", "direction_is_long", "direction_is_short"],
        "metrics": {"validation_expected_r_per_candidate": 0.002, "test_expected_r_per_candidate": -0.001},
        "promotion_allowed": False,
    }


def model_diagnostics() -> dict:
    return {
        "report_id": "b" * 64,
        "status": "FEATURE_DIAGNOSTICS_REQUIRED",
        "blocked_reasons": ["NEGATIVE_TEST_EXPECTED_R", "TEST_ACCURACY_NOT_ABOVE_BASELINE"],
        "promotion_allowed": False,
    }


def test_gc_feature_diagnostics_cli_writes_report(tmp_path: Path):
    rows_root = tmp_path / "market-data/gc-30m-real" / "fixture-dataset"
    rows_root.mkdir(parents=True)
    rows_path = rows_root / "rows.parquet"
    rows().to_parquet(rows_path, index=False)
    manifest = build_manifest()
    manifest["rows_relative_dir"] = "fixture-dataset"
    manifest["rows_file"] = "rows.parquet"
    manifest_path = tmp_path / "build-manifest.json"
    first_model_path = tmp_path / "first-model.json"
    diagnostics_path = tmp_path / "model-diagnostics.json"
    report_out = tmp_path / "feature-diagnostics.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    first_model_path.write_text(json.dumps(first_model_run()), encoding="utf-8")
    diagnostics_path.write_text(json.dumps(model_diagnostics()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_feature_diagnostics.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(tmp_path / "market-data/gc-30m-real"),
            "--first-model-run",
            str(first_model_path),
            "--model-diagnostics",
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
    assert payload["status"] == "EXPERIMENT_DESIGN_REQUIRED"
    assert payload["promotion_allowed"] is False
    assert "ORDER_FLOW_FEATURE_STABILITY_REVIEW" in payload["recommended_experiments"]
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

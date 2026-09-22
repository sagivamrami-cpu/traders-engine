import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd

from trading_system.data_foundation.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[2]
_RUN_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "gc_bounded_walk_forward_retraining_fixture",
    ROOT / "tests/models/test_gc_bounded_walk_forward_retraining.py",
)
if _RUN_FIXTURE_SPEC is None or _RUN_FIXTURE_SPEC.loader is None:
    raise RuntimeError("bounded walk-forward fixture could not be loaded")
_RUN_FIXTURE_MODULE = importlib.util.module_from_spec(_RUN_FIXTURE_SPEC)
_RUN_FIXTURE_SPEC.loader.exec_module(_RUN_FIXTURE_MODULE)
experiment_plan = _RUN_FIXTURE_MODULE.experiment_plan

_DATASET_SPEC = importlib.util.spec_from_file_location(
    "first_real_model_cli_fixture",
    ROOT / "tests/models/test_train_gc_first_real_model_cli.py",
)
if _DATASET_SPEC is None or _DATASET_SPEC.loader is None:
    raise RuntimeError("first real model CLI fixture could not be loaded")
_DATASET_MODULE = importlib.util.module_from_spec(_DATASET_SPEC)
_DATASET_SPEC.loader.exec_module(_DATASET_MODULE)
DATASET_ID = _DATASET_MODULE.DATASET_ID
write_tiny_phase46_dataset = _DATASET_MODULE.write_tiny_phase46_dataset

_FEATURE_SPEC = importlib.util.spec_from_file_location(
    "normalized_feature_model_cli_fixture",
    ROOT / "tests/models/test_train_gc_normalized_feature_model_cli.py",
)
if _FEATURE_SPEC is None or _FEATURE_SPEC.loader is None:
    raise RuntimeError("normalized feature model CLI fixture could not be loaded")
_FEATURE_MODULE = importlib.util.module_from_spec(_FEATURE_SPEC)
_FEATURE_SPEC.loader.exec_module(_FEATURE_MODULE)
feature_candidates = _FEATURE_MODULE.feature_candidates


def write_walk_forward_dataset(tmp_path: Path) -> tuple[Path, Path]:
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    rows_path = rows_root / DATASET_ID[:16] / "rows.parquet"
    records = []
    index = 0
    for month in range(1, 7):
        split = "TEST" if month >= 4 else "TRAIN"
        for direction, outcome, ret_1, of_delta in (
            ("LONG", "TARGET_FIRST", 0.05, 8.0),
            ("LONG", "STOP_FIRST", -0.02, -2.0),
            ("SHORT", "TARGET_FIRST", 0.03, 4.0),
            ("SHORT", "STOP_FIRST", -0.04, -7.0),
        ):
            index += 1
            records.append(
                {
                    "dataset_id": DATASET_ID,
                    "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
                    "candidate_id": f"candidate-{index}",
                    "bar_start": pd.Timestamp(f"2026-{month:02d}-15T00:00:00Z"),
                    "bar_end": pd.Timestamp(f"2026-{month:02d}-15T00:30:00Z"),
                    "direction": direction,
                    "split": split,
                    "included_ohlcv_only": True,
                    "included_order_flow": True,
                    "outcome_class": outcome,
                    "label_quality": "HIGH",
                    "exclusion_reasons_ohlcv_only": "",
                    "exclusion_reasons_order_flow": "",
                    "close": 1000.0 + month,
                    "atr_14": 2.0 if month == 1 else 6.0,
                    "ret_1": ret_1,
                    "ret_4": ret_1 * 2,
                    "ret_8": ret_1 * 3,
                    "ret_14": ret_1 * 4,
                    "range_over_atr": abs(ret_1) + 1.0,
                    "volume_30m": 100,
                    "seconds_with_trades": 120,
                    "of_volume": 100,
                    "of_delta": of_delta,
                    "of_trades": 3,
                    "of_minutes_present": 30,
                    "of_volume_sum_14": 1400,
                    "of_delta_sum_14": of_delta * 14,
                    "of_trades_sum_14": 42,
                    "net_return_r": 1.0 if outcome == "TARGET_FIRST" else -1.0,
                }
            )
    frame = pd.DataFrame(records)
    frame.to_parquet(rows_path, index=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rows_count"] = len(frame)
    manifest["rows_sha256"] = sha256_file(rows_path)
    manifest["rows_columns"] = list(frame.columns)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, rows_root


def test_run_gc_bounded_walk_forward_retraining_cli_writes_sanitized_run(tmp_path: Path):
    manifest_path, rows_root = write_walk_forward_dataset(tmp_path)
    candidates_path = tmp_path / "feature-candidates.json"
    experiments_path = tmp_path / "experiments.json"
    run_out = tmp_path / "walk-forward-run.json"
    candidates_path.write_text(json.dumps(feature_candidates()), encoding="utf-8")
    experiments_path.write_text(json.dumps(experiment_plan()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/run_gc_bounded_walk_forward_retraining.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
            "--feature-candidates",
            str(candidates_path),
            "--experiment-report",
            str(experiments_path),
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
    assert payload["status"] == "WALK_FORWARD_RETRAINING_EXECUTED"
    assert payload["model_promotion_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(run_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

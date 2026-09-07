import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from trading_system.data_foundation.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966"


def write_tiny_phase46_dataset(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "market-data/gc-30m-real" / DATASET_ID[:16]
    dataset_dir.mkdir(parents=True)
    rows = []
    samples = [
        ("TRAIN", "TARGET_FIRST", 0.05, 9.0),
        ("TRAIN", "TARGET_FIRST", 0.04, 8.0),
        ("TRAIN", "STOP_FIRST", -0.05, -9.0),
        ("TRAIN", "STOP_FIRST", -0.04, -8.0),
        ("VALIDATION", "TARGET_FIRST", 0.045, 8.5),
        ("VALIDATION", "STOP_FIRST", -0.045, -8.5),
        ("TEST", "TARGET_FIRST", 0.046, 8.6),
        ("TEST", "STOP_FIRST", -0.046, -8.6),
    ]
    for index, (split, outcome, ret_1, of_delta) in enumerate(samples, start=1):
        rows.append(
            {
                "dataset_id": DATASET_ID,
                "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
                "candidate_id": f"candidate-{index}",
                "bar_start": pd.Timestamp(f"2026-09-{index:02d}T00:00:00Z"),
                "bar_end": pd.Timestamp(f"2026-09-{index:02d}T00:30:00Z"),
                "direction": "LONG" if ret_1 >= 0 else "SHORT",
                "split": split,
                "included_ohlcv_only": True,
                "included_order_flow": True,
                "outcome_class": outcome,
                "label_quality": "HIGH",
                "exclusion_reasons_ohlcv_only": "",
                "exclusion_reasons_order_flow": "",
                "close": 1000.0 + index,
                "atr_14": 4.0,
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
            }
        )
    frame = pd.DataFrame(rows)
    rows_path = dataset_dir / "rows.parquet"
    frame.to_parquet(rows_path, index=False)
    manifest = {
        "manifest_id": "a" * 64,
        "manifest_version": "gc-30m-real-dataset-build-manifest-0.1.0",
        "mode": "GC_REAL_DATASET_BUILD",
        "created_at": "2026-09-07T13:00:00Z",
        "dataset_id": DATASET_ID,
        "dataset_name": "gc-30m-real-research-dataset",
        "identity_manifest_id": "b" * 64,
        "identity_source": "LOCAL_ARCHIVE_VERIFIED",
        "builder_version": "gc-30m-real-dataset-builder-0.1.0",
        "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
        "label_version": "gc-outcome-contract-label-0.1.0",
        "contract_version": "gc-atr14-1r-1r-8bar-zero-cost-0.1.0",
        "authorization_record_refs": [
            "agent-exchange/decisions/2026-09-02T162000Z-human-d9-final-dataset-construction-authorization-gc-30m-f9d3c1b0.md"
        ],
        "source_hashes": {"ohlcv_1s_zip": "c" * 64, "order_flow_zip": "d" * 64},
        "ohlcv_source_stats": {"members_read": 1, "source_rows_1s": 8, "bars_30m_with_data": 8},
        "order_flow_source_stats": {
            "member": "gc/GCext_of_1m.parquet",
            "source_rows_1m": 8,
            "bars_30m_with_order_flow": 8,
        },
        "rows_file": "rows.parquet",
        "rows_relative_dir": DATASET_ID[:16],
        "rows_sha256": sha256_file(rows_path),
        "rows_count": len(frame),
        "rows_columns": list(frame.columns),
        "summary": {
            "expected_session_bars": 8,
            "present_session_bars": 8,
            "missing_expected_bars": 0,
            "missing_expected_bars_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
            "missing_expected_bars_by_trade_date": {},
            "rows_total": len(frame),
            "rows_by_split": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
            "variants": {
                "ohlcv_only": {
                    "included_rows": 8,
                    "excluded_rows": 0,
                    "included_rows_by_split": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
                    "excluded_rows_by_reason": {},
                    "excluded_rows_by_reason_and_split": {},
                    "included_outcome_class_counts": {"TARGET_FIRST": 4, "STOP_FIRST": 4},
                },
                "order_flow": {
                    "included_rows": 8,
                    "excluded_rows": 0,
                    "included_rows_by_split": {"TRAIN": 4, "VALIDATION": 2, "TEST": 2},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
                    "excluded_rows_by_reason": {},
                    "excluded_rows_by_reason_and_split": {},
                    "included_outcome_class_counts": {"TARGET_FIRST": 4, "STOP_FIRST": 4},
                },
            },
            "out_of_session_bars_with_data": 0,
            "straddle_bars": 0,
            "straddle_bars_with_data": 0,
            "first_bar_start": "2026-09-01T00:00:00Z",
            "last_bar_start": "2026-09-08T00:00:00Z",
            "rules": {"builder_version": "gc-30m-real-dataset-builder-0.1.0"},
        },
        "contract_identity_status": "UNDECLARED_PENDING_RESEARCH",
        "real_dataset_built": True,
        "training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
    }
    manifest_path = tmp_path / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, tmp_path / "market-data/gc-30m-real"


def test_train_gc_first_real_model_cli_writes_sanitized_run(tmp_path: Path):
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    run_out = tmp_path / "run.json"
    result = subprocess.run(
        [
            sys.executable,
            "tools/train_gc_first_real_model.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
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
    assert payload["model_type"] == "REGULARIZED_LOGISTIC_RESEARCH_BASELINE"
    assert payload["promotion_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(run_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""

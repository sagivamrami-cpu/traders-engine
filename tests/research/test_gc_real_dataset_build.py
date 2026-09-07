from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_real_dataset_build_manifest.schema.json"
DATASET_ID = "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966"
AUTHORIZATION_REF = (
    "agent-exchange/decisions/2026-09-02T162000Z-human-d9-final-dataset-construction-authorization-gc-30m-f9d3c1b0.md"
)


def validate_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def minimal_valid_build_manifest() -> dict:
    return {
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
        "authorization_record_refs": [AUTHORIZATION_REF],
        "source_hashes": {
            "ohlcv_1s_zip": "b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1",
            "order_flow_zip": "34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155",
        },
        "ohlcv_source_stats": {
            "members_read": 1,
            "source_rows_1s": 120,
            "bars_30m_with_data": 120,
        },
        "order_flow_source_stats": {
            "member": "gc/GCext_of_1m.parquet",
            "source_rows_1m": 120,
            "bars_30m_with_order_flow": 120,
        },
        "rows_file": "rows.parquet",
        "rows_relative_dir": DATASET_ID[:16],
        "rows_sha256": "c" * 64,
        "rows_count": 200,
        "rows_columns": [
            "dataset_id",
            "dataset_version",
            "candidate_id",
            "bar_start",
            "bar_end",
            "direction",
            "split",
            "included_ohlcv_only",
            "included_order_flow",
            "outcome_class",
            "label_quality",
            "exclusion_reasons_ohlcv_only",
            "exclusion_reasons_order_flow",
        ],
        "summary": {
            "expected_session_bars": 120,
            "present_session_bars": 120,
            "missing_expected_bars": 0,
            "missing_expected_bars_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
            "missing_expected_bars_by_trade_date": {},
            "rows_total": 200,
            "rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 200},
            "variants": {
                "ohlcv_only": {
                    "included_rows": 150,
                    "excluded_rows": 50,
                    "included_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 150},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 50},
                    "excluded_rows_by_reason": {"INSUFFICIENT_LOOKBACK": 30},
                    "excluded_rows_by_reason_and_split": {
                        "INSUFFICIENT_LOOKBACK": {"TRAIN": 0, "VALIDATION": 0, "TEST": 30}
                    },
                    "included_outcome_class_counts": {"TARGET_FIRST": 80, "STOP_FIRST": 70},
                },
                "order_flow": {
                    "included_rows": 140,
                    "excluded_rows": 60,
                    "included_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 140},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 60},
                    "excluded_rows_by_reason": {"ORDER_FLOW_MISSING_FOR_ACTIVE_BAR": 10},
                    "excluded_rows_by_reason_and_split": {
                        "ORDER_FLOW_MISSING_FOR_ACTIVE_BAR": {"TRAIN": 0, "VALIDATION": 0, "TEST": 10}
                    },
                    "included_outcome_class_counts": {"TARGET_FIRST": 75, "STOP_FIRST": 65},
                },
            },
            "out_of_session_bars_with_data": 0,
            "straddle_bars": 0,
            "straddle_bars_with_data": 0,
            "first_bar_start": "2026-09-01T00:00:00Z",
            "last_bar_start": "2026-09-03T12:00:00Z",
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


def test_build_manifest_schema_accepts_sanitized_real_build_payload():
    payload = minimal_valid_build_manifest()
    validate_payload(payload)
    dumped = json.dumps(payload, ensure_ascii=True)
    assert "C:\\" not in dumped
    assert "/Users/" not in dumped
    assert payload["training_allowed"] is False
    assert payload["model_promotion_allowed"] is False


@pytest.mark.parametrize("field", ["training_allowed", "model_promotion_allowed"])
def test_build_manifest_schema_never_allows_training_or_promotion(field: str):
    payload = minimal_valid_build_manifest()
    payload[field] = True
    with pytest.raises(Exception):
        validate_payload(payload)


def test_build_manifest_class_validates_against_schema():
    from trading_system.research.gc_real_dataset_build import GcRealDatasetBuildManifest

    payload = minimal_valid_build_manifest()
    manifest = GcRealDatasetBuildManifest(payload=payload)
    assert manifest.to_payload()["real_dataset_built"] is True


def test_build_dataset_cli_help_is_available():
    result = subprocess.run(
        [sys.executable, "tools/build_gc_30m_real_dataset.py", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "--ohlcv-zip" in result.stdout
    assert "--order-flow-zip" in result.stdout
    assert "--manifest-out" in result.stdout
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

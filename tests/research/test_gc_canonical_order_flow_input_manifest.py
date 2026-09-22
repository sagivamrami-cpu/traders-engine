import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs/data/gc-canonical-order-flow-input-manifest.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_canonical_order_flow_input_manifest.schema.json"
CREATED_AT = datetime(2026, 9, 2, 4, 0, tzinfo=UTC)
GC_ORDER_FLOW_SHA256 = "34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155"


def validate_manifest_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_canonical_order_flow_input_manifest_records_selected_member_without_authorizing_features():
    from trading_system.research.gc_canonical_order_flow_input_manifest import (
        build_gc_canonical_order_flow_input_manifest_report,
    )

    payload = build_gc_canonical_order_flow_input_manifest_report(
        MANIFEST_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_manifest_payload(payload)
    assert payload["status"] == "CANONICAL_ORDER_FLOW_INPUT_RECORDED_NOT_SOURCE_AUTHORIZED"
    assert payload["canonical_symbol"] == "GC"
    assert payload["source_type"] == "DATABENTO_LOCAL_GC_ORDER_FLOW_ZIP"
    assert payload["archive_sha256"] == GC_ORDER_FLOW_SHA256
    assert payload["archive_size_bytes"] == 2496805183
    assert payload["archive_member_count"] == 30
    assert payload["parquet_member_count"] == 5
    assert payload["selected_member"] == "gc/GCext_of_1m.parquet"
    assert payload["selected_member_role"] == "ORDER_FLOW_1M_LONGEST_HISTORY_NO_ARCHIVED_CVD"
    assert payload["selected_member_row_count"] == 5388775
    assert payload["selected_member_columns"] == ["volume", "delta", "trades", "minute"]
    assert payload["selected_member_start_at"] == "2011-01-02T23:00:00Z"
    assert payload["selected_member_end_at"] == "2026-07-17T20:59:00Z"
    assert payload["timestamp_role"] == "MINUTE_START_APPROVED_V1"
    assert payload["timezone_policy"] == "LOCALIZE_NAIVE_AS_UTC_WALL_CLOCK_APPROVED_V1"
    assert payload["known_damaged_aggressor_window"]["status"] == "EXCLUDE_FROM_ORDER_FLOW_FEATURES"
    assert payload["archived_cvd_policy"] == "FORBIDDEN_RECOMPUTE_PIT_FOLD_LOCAL_IF_USED"
    assert payload["canonical_order_flow_input_gate_status"] == "SATISFIED_FOR_INPUT_IDENTITY_ONLY"
    assert payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION"
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_NOT_ROW_MASKED"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert "BUILD_ORDER_FLOW_FEATURES" in payload["blocked_actions"]


def test_gc_canonical_order_flow_input_manifest_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_canonical_order_flow_input_manifest.py",
            "--manifest",
            "configs/data/gc-canonical-order-flow-input-manifest.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_manifest_payload(payload)
    assert payload["archive_sha256"] == GC_ORDER_FLOW_SHA256
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

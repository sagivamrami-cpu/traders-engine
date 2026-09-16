import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs/data/gc-canonical-ohlcv-input-manifest.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_canonical_ohlcv_input_manifest.schema.json"
CREATED_AT = datetime(2026, 9, 2, 3, 0, tzinfo=UTC)
GC_1S_SHA256 = "b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1"


def validate_manifest_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_canonical_ohlcv_input_manifest_records_identity_without_authorizing_dataset():
    from trading_system.research.gc_canonical_ohlcv_input_manifest import (
        build_gc_canonical_ohlcv_input_manifest_report,
    )

    payload = build_gc_canonical_ohlcv_input_manifest_report(
        MANIFEST_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_manifest_payload(payload)
    assert payload["status"] == "CANONICAL_OHLCV_INPUT_RECORDED_NOT_DATASET_AUTHORIZED"
    assert payload["canonical_symbol"] == "GC"
    assert payload["source_type"] == "DATABENTO_LOCAL_GC_1S_ZIP"
    assert payload["archive_sha256"] == GC_1S_SHA256
    assert payload["archive_size_bytes"] == 984191105
    assert payload["timestamp_role"] == "TS_EVENT_INTERVAL_START_APPROVED_V1"
    assert payload["local_path"] == "LOCAL_PATH_REDACTED"
    assert payload["canonical_ohlcv_input_gate_status"] == "SATISFIED_FOR_OHLCV_ONLY"
    assert payload["dataset_identity_gate_status"] == "UNSATISFIED_PARTIAL_INPUT_IDENTITY_ONLY"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False


def test_gc_canonical_ohlcv_input_manifest_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_canonical_ohlcv_input_manifest.py",
            "--manifest",
            "configs/data/gc-canonical-ohlcv-input-manifest.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_manifest_payload(payload)
    assert payload["archive_sha256"] == GC_1S_SHA256
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

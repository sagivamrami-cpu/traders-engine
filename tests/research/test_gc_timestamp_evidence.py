import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_timestamp_evidence_report.schema.json"
CREATED_AT = datetime(2026, 9, 1, 22, 30, tzinfo=UTC)


def validate_timestamp_evidence_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def write_timestamp_fixture_zip(path: Path) -> Path:
    aware = pd.DataFrame(
        {
            "gc_open": [1.0],
            "gc_high": [1.0],
            "gc_low": [1.0],
            "gc_close": [1.0],
            "gc_volume": [1.0],
            "ts_event": pd.to_datetime(["2026-01-01T00:00:00Z"]),
        }
    )
    naive = pd.DataFrame(
        {
            "volume": [1.0],
            "delta": [0.0],
            "trades": [1],
            "minute": pd.to_datetime(["2026-01-01T00:00:00"]),
        }
    )
    aware_buffer = io.BytesIO()
    naive_buffer = io.BytesIO()
    aware.to_parquet(aware_buffer, engine="pyarrow")
    naive.to_parquet(naive_buffer, engine="pyarrow")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("gc_1s/gc_1s_2026-01.parquet", aware_buffer.getvalue())
        archive.writestr("gc/GCext_of_1m.parquet", naive_buffer.getvalue())
        archive.writestr(
            "gc/README.md",
            "The naive timestamps are UTC wall-clock. Do not average through the 2017 window.",
        )
    return path


def minimal_valid_timestamp_evidence_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-timestamp-evidence-report-0.1.0",
        "mode": "GC_TIMESTAMP_EVIDENCE",
        "created_at": "2026-09-01T22:30:00Z",
        "status": "EVIDENCE_COLLECTED_NEEDS_HUMAN_DECISION",
        "canonical_symbol": "GC",
        "dataset_construction_allowed": False,
        "resampling_allowed": False,
        "training_allowed": False,
        "sources": [
            {
                "source_role": "HISTORICAL_OHLCV_1S_ZIP",
                "local_path": "LOCAL_PATH_REDACTED",
                "inspected_members": [
                    {
                        "member": "gc_1s/gc_1s_2026-01.parquet",
                        "row_count": 1,
                        "timestamp_column": "ts_event",
                        "timestamp_type": "timestamp[ns, tz=UTC]",
                        "timezone_status": "UTC_AWARE",
                        "role_evidence_status": "COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN",
                    }
                ],
            },
            {
                "source_role": "ORDER_FLOW_1M_ZIP",
                "local_path": "LOCAL_PATH_REDACTED",
                "readme_evidence": {
                    "readme_present": True,
                    "naive_utc_wall_clock_claim_present": True,
                    "damaged_2017_warning_present": True,
                },
                "inspected_members": [
                    {
                        "member": "gc/GCext_of_1m.parquet",
                        "row_count": 1,
                        "timestamp_column": "minute",
                        "timestamp_type": "timestamp[ns]",
                        "timezone_status": "TIMEZONE_NAIVE_UTC_WALL_CLOCK_CLAIM_REQUIRES_DECISION",
                        "role_evidence_status": "ONE_MINUTE_AGGREGATE_COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN",
                    }
                ],
            },
        ],
        "evidence_summary": {
            "ohlcv_1s_ts_event_timezone": "UTC_AWARE",
            "order_flow_minute_timezone_mix": "MIXED_OR_NAIVE_REQUIRES_POLICY",
            "naive_order_flow_utc_localization_candidate": True,
            "timestamp_role_gate_status": "UNSATISFIED_EVIDENCE_ONLY",
        },
        "required_human_decisions": [
            "D3_CONFIRM_OHLCV_TS_EVENT_START_OR_REJECT",
            "D3_CONFIRM_ORDER_FLOW_MINUTE_START_AND_UTC_LOCALIZATION_OR_REJECT",
        ],
        "blocked_actions": [
            "RESAMPLE_REAL_BARS",
            "JOIN_ORDER_FLOW_TO_OHLCV",
            "BUILD_REAL_DATASET",
            "BUILD_REAL_LABELS",
            "TRAIN_PRODUCTION_MODEL",
        ],
    }


def test_gc_timestamp_evidence_schema_accepts_metadata_only_payload():
    payload = minimal_valid_timestamp_evidence_payload()
    validate_timestamp_evidence_payload(payload)
    assert payload["status"] == "EVIDENCE_COLLECTED_NEEDS_HUMAN_DECISION"
    assert payload["sources"][0]["local_path"] == "LOCAL_PATH_REDACTED"
    assert payload["dataset_construction_allowed"] is False


def test_gc_timestamp_evidence_reads_zip_metadata_without_raw_values(tmp_path: Path):
    from trading_system.research.gc_timestamp_evidence import build_gc_timestamp_evidence_report

    fixture_zip = write_timestamp_fixture_zip(tmp_path / "gc-fixture.zip")
    payload = build_gc_timestamp_evidence_report(
        ohlcv_zip_path=fixture_zip,
        order_flow_zip_path=fixture_zip,
        created_at=CREATED_AT,
    ).to_payload()

    validate_timestamp_evidence_payload(payload)
    assert payload["sources"][0]["inspected_members"][0]["timestamp_column"] == "ts_event"
    assert payload["sources"][0]["inspected_members"][0]["timezone_status"] == "UTC_AWARE"
    assert payload["sources"][1]["readme_evidence"]["naive_utc_wall_clock_claim_present"] is True
    assert payload["sources"][1]["inspected_members"][0]["timezone_status"] == (
        "TIMEZONE_NAIVE_UTC_WALL_CLOCK_CLAIM_REQUIRES_DECISION"
    )
    assert "D3_CONFIRM_ORDER_FLOW_MINUTE_START_AND_UTC_LOCALIZATION_OR_REJECT" in (
        payload["required_human_decisions"]
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert str(fixture_zip) not in serialized
    assert "gc_open" not in serialized
    assert "delta" not in serialized


def test_gc_timestamp_evidence_cli_outputs_sanitized_json(tmp_path: Path):
    fixture_zip = write_timestamp_fixture_zip(tmp_path / "gc-fixture.zip")
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_timestamp_evidence.py",
            "--ohlcv-zip",
            str(fixture_zip),
            "--order-flow-zip",
            str(fixture_zip),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_timestamp_evidence_payload(payload)
    assert payload["training_allowed"] is False
    assert str(fixture_zip) not in result.stdout
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

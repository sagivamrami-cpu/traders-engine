import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
STRATEGY_PATH = ROOT / "configs/data/gc-session-calendar-source-strategy.yaml"
DECISION_PATH = ROOT / "agent-exchange/decisions/2026-09-01T185500Z-human-d2-session-calendar-source-strategy-v1.md"
STRATEGY_SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_source_strategy.schema.json"
OBSERVED_SCHEMA_PATH = ROOT / "schemas/gc_observed_activity_calendar_profile.schema.json"
CREATED_AT = datetime(2026, 9, 1, 23, 30, tzinfo=UTC)


def validate_strategy_payload(payload: dict) -> None:
    schema = load_json(STRATEGY_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def validate_observed_payload(payload: dict) -> None:
    schema = load_json(OBSERVED_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def write_gc_1s_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_1s_activity.zip"
    frames = {
        "gc_1s/gc_1s_2020-01.parquet": pd.DataFrame(
            {
                "gc_open": [100.0, 100.1, 100.2],
                "gc_high": [100.2, 100.3, 100.4],
                "gc_low": [99.9, 100.0, 100.1],
                "gc_close": [100.1, 100.2, 100.3],
                "gc_volume": [1.0, 2.0, 3.0],
            },
            index=pd.DatetimeIndex(
                pd.to_datetime(
                    [
                        "2020-01-01T00:00:00Z",
                        "2020-01-01T00:00:01Z",
                        "2020-01-01T00:30:00Z",
                    ]
                ),
                name="ts_event",
            ),
        ),
        "gc_1s/gc_1s_2020-02.parquet": pd.DataFrame(
            {
                "gc_open": [101.0, 101.1],
                "gc_high": [101.2, 101.3],
                "gc_low": [100.9, 101.0],
                "gc_close": [101.1, 101.2],
                "gc_volume": [4.0, 5.0],
            },
            index=pd.DatetimeIndex(
                pd.to_datetime(["2020-02-01T00:00:00Z", "2020-02-01T00:00:01Z"]),
                name="ts_event",
            ),
        ),
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, frame in frames.items():
            buffer = io.BytesIO()
            frame.to_parquet(buffer, engine="pyarrow")
            archive.writestr(name, buffer.getvalue())
    return zip_path


def test_d2_decision_record_exists_and_is_source_strategy_only():
    text = DECISION_PATH.read_text(encoding="utf-8")

    assert "Decision: APPROVED_SOURCE_STRATEGY_V1_NOT_CALENDAR_AUTHORIZATION" in text
    assert "No Databento API query" in text
    assert "No real bar resampling" in text
    assert "No model training" in text


def test_gc_session_calendar_source_strategy_report_is_fail_closed():
    from trading_system.research.gc_session_calendar_source_strategy import (
        build_gc_session_calendar_source_strategy_report,
    )

    payload = build_gc_session_calendar_source_strategy_report(
        STRATEGY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_strategy_payload(payload)
    assert payload["status"] == "SOURCE_STRATEGY_APPROVED_CALENDAR_IMPLEMENTATION_REQUIRED"
    assert payload["decision_ref"] == "agent-exchange/decisions/2026-09-01T185500Z-human-d2-session-calendar-source-strategy-v1.md"
    assert payload["session_calendar_gate_status"] == "UNSATISFIED_SOURCE_STRATEGY_ONLY"
    assert payload["calendar_registration_allowed"] is False
    assert payload["databento_status_leg"]["query_allowed"] is False
    assert payload["databento_status_leg"]["status"] == "BLOCKED_PENDING_SEPARATE_COST_SOURCE_APPROVAL"
    assert payload["observed_activity_leg"]["status"] == "APPROVED_FIRST_ZERO_COST_EVIDENCE_LEG"
    assert payload["cme_official_leg"]["status"] == "REQUIRED_AUTHORITATIVE_PUBLIC_REFERENCE"
    assert payload["tradingview_leg"]["status"] == "NON_AUTHORITATIVE_SANITY_CHECK_ONLY"
    assert payload["era_versioning"]["required"] is True
    assert payload["scheduled_vs_observed_policy"] == "SEPARATE_REQUIRED_FAIL_ON_DISAGREEMENT"
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert "REGISTER_SESSION_CALENDAR" in payload["blocked_actions"]


def test_phase31_rejects_pending_gc_calendar_registration(tmp_path: Path):
    from tools.validate_phase31 import assert_pending_gc_metals_calendar_absent

    calendar_path = tmp_path / "session-calendar.yaml"
    calendar_path.write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "calendars": {
                    "us-equities-regular-v1": {},
                    "cme-globex-metals-research-pending-v1": {},
                },
            }
        ),
        encoding="utf-8",
    )

    try:
        assert_pending_gc_metals_calendar_absent(calendar_path)
    except ValueError as exc:
        assert "pending GC metals calendar cannot be registered before D2 implementation" in str(exc)
    else:
        raise AssertionError("Phase 31 must reject pending GC calendar registration")


def test_observed_activity_profile_reads_sanitized_aggregate_without_authorizing_calendar(tmp_path: Path):
    from trading_system.research.gc_session_calendar_source_strategy import (
        build_gc_observed_activity_calendar_profile,
    )

    zip_path = write_gc_1s_zip(tmp_path)
    payload = build_gc_observed_activity_calendar_profile(
        zip_path,
        STRATEGY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_observed_payload(payload)
    assert payload["status"] == "OBSERVED_ACTIVITY_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert payload["local_path"] == "LOCAL_PATH_REDACTED"
    assert payload["parquet_entry_count"] == 2
    assert payload["sampled_entry_count"] == 2
    assert payload["row_count"] == 5
    assert payload["first_observed_at"] == "2020-01-01T00:00:00Z"
    assert payload["last_observed_at"] == "2020-02-01T00:00:01Z"
    assert payload["largest_sampled_gap_seconds"] == 2676600
    assert payload["session_calendar_gate_status"] == "UNSATISFIED_OBSERVED_ACTIVITY_ONLY"
    assert payload["calendar_registration_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_gc_session_calendar_source_strategy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_session_calendar_source_strategy.py",
            "--strategy",
            "configs/data/gc-session-calendar-source-strategy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_strategy_payload(payload)
    assert payload["status"] == "SOURCE_STRATEGY_APPROVED_CALENDAR_IMPLEMENTATION_REQUIRED"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""


def test_observed_activity_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_gc_1s_zip(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_observed_activity_calendar.py",
            "--zip",
            str(zip_path),
            "--strategy",
            "configs/data/gc-session-calendar-source-strategy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_observed_payload(payload)
    assert payload["status"] == "OBSERVED_ACTIVITY_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(zip_path) not in result.stdout
    assert str(tmp_path) not in result.stdout

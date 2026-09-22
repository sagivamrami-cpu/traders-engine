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
STRATEGY_PATH = ROOT / "configs/data/gc-session-calendar-source-strategy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_observed_activity_full_aggregate.schema.json"
CREATED_AT = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)


def validate_full_aggregate_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def write_gc_1s_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_1s_activity.zip"
    frames = {
        "gc_1s/gc_1s_2020-01.parquet": pd.DataFrame(
            {"gc_close": [100.1, 100.2, 100.3]},
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
            {"gc_close": [101.1, 101.2]},
            index=pd.DatetimeIndex(
                pd.to_datetime(["2020-02-01T00:00:00Z", "2020-02-01T00:00:01Z"]),
                name="ts_event",
            ),
        ),
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, frame in frames.items():
            archive.writestr(name, frame.to_parquet(engine="pyarrow"))
    return zip_path


def test_full_aggregate_uses_parquet_metadata_without_authorizing_calendar(tmp_path: Path):
    from trading_system.research.gc_session_calendar_source_strategy import (
        build_gc_observed_activity_full_aggregate,
    )

    zip_path = write_gc_1s_zip(tmp_path)
    payload = build_gc_observed_activity_full_aggregate(
        zip_path,
        STRATEGY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_full_aggregate_payload(payload)
    assert payload["status"] == "FULL_OBSERVED_ACTIVITY_AGGREGATE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert payload["local_path"] == "LOCAL_PATH_REDACTED"
    assert payload["parquet_entry_count"] == 2
    assert payload["row_count"] == 5
    assert payload["first_observed_at"] == "2020-01-01T00:00:00Z"
    assert payload["last_observed_at"] == "2020-02-01T00:00:01Z"
    assert payload["largest_inter_member_gap_seconds"] == 2676600
    assert [period["member"] for period in payload["periods"]] == [
        "gc_1s/gc_1s_2020-01.parquet",
        "gc_1s/gc_1s_2020-02.parquet",
    ]
    assert payload["periods"][0]["row_count"] == 3
    assert payload["periods"][1]["row_count"] == 2
    assert payload["metadata_only"] is True
    assert payload["calendar_registration_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_full_aggregate_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_gc_1s_zip(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_observed_activity_full_aggregate.py",
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
    validate_full_aggregate_payload(payload)
    assert payload["status"] == "FULL_OBSERVED_ACTIVITY_AGGREGATE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(zip_path) not in result.stdout
    assert str(tmp_path) not in result.stdout
    assert result.stderr == ""

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
STRATEGY_PATH = ROOT / "configs/data/gc-session-calendar-source-strategy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_fine_observed_gap_profile.schema.json"
CREATED_AT = datetime(2026, 9, 2, 2, 0, tzinfo=UTC)


def validate_gap_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _write_parquet(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def write_gap_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_1s_gap_profile.zip"
    frames = {
        "gc_1s/gc_1s_2020-01.parquet": pd.DataFrame(
            {"gc_close": [100.0, 100.1, 100.2, 100.3]},
            index=pd.DatetimeIndex(
                pd.to_datetime(
                    [
                        "2020-01-01T00:00:00Z",
                        "2020-01-01T00:00:01Z",
                        "2020-01-01T00:00:05Z",
                        "2020-01-01T00:00:06Z",
                    ]
                ),
                name="ts_event",
            ),
        ),
        "gc_1s/gc_1s_2020-02.parquet": pd.DataFrame(
            {"gc_close": [101.0, 101.1]},
            index=pd.DatetimeIndex(
                pd.to_datetime(["2020-02-01T00:00:00Z", "2020-02-01T00:00:10Z"]),
                name="ts_event",
            ),
        ),
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, frame in frames.items():
            archive.writestr(name, _write_parquet(frame))
    return zip_path


def test_fine_observed_gap_profile_reads_timestamps_only_and_stays_fail_closed(tmp_path: Path):
    from trading_system.research.gc_fine_observed_gap_profile import (
        build_gc_fine_observed_gap_profile,
    )

    zip_path = write_gap_zip(tmp_path)
    payload = build_gc_fine_observed_gap_profile(
        zip_path,
        STRATEGY_PATH,
        created_at=CREATED_AT,
        top_n_gaps=3,
    ).to_payload()

    validate_gap_payload(payload)
    assert payload["status"] == "FINE_OBSERVED_GAP_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert payload["local_path"] == "LOCAL_PATH_REDACTED"
    assert payload["timestamp_column_only"] is True
    assert payload["expected_cadence_seconds"] == 1
    assert payload["parquet_entry_count"] == 2
    assert payload["row_count"] == 6
    assert payload["largest_gap_seconds"] == 10
    assert payload["nonconsecutive_transition_count"] == 2
    assert payload["periods"][0]["largest_gap_seconds"] == 4
    assert payload["periods"][0]["timestamp_order_status"] == "ALREADY_MONOTONIC"
    assert payload["periods"][1]["largest_gap_seconds"] == 10
    assert payload["periods"][1]["timestamp_order_status"] == "ALREADY_MONOTONIC"
    assert payload["top_gaps"][0]["gap_seconds"] == 10
    assert payload["top_gaps"][1]["gap_seconds"] == 4
    assert payload["calendar_registration_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_fine_observed_gap_profile_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_gap_zip(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_fine_observed_gap_profile.py",
            "--zip",
            str(zip_path),
            "--strategy",
            "configs/data/gc-session-calendar-source-strategy.yaml",
            "--top-n-gaps",
            "3",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_gap_payload(payload)
    assert payload["status"] == "FINE_OBSERVED_GAP_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(zip_path) not in result.stdout
    assert str(tmp_path) not in result.stdout
    assert result.stderr == ""


def test_fine_observed_gap_profile_cli_can_limit_members_for_bounded_smoke(tmp_path: Path):
    zip_path = write_gap_zip(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_fine_observed_gap_profile.py",
            "--zip",
            str(zip_path),
            "--strategy",
            "configs/data/gc-session-calendar-source-strategy.yaml",
            "--top-n-gaps",
            "3",
            "--max-members",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_gap_payload(payload)
    assert payload["parquet_entry_count"] == 1
    assert payload["row_count"] == 4
    assert [period["member"] for period in payload["periods"]] == ["gc_1s/gc_1s_2020-01.parquet"]


def test_fine_observed_gap_profile_records_when_member_timestamps_are_sorted(tmp_path: Path):
    from trading_system.research.gc_fine_observed_gap_profile import (
        build_gc_fine_observed_gap_profile,
    )

    zip_path = tmp_path / "gc_1s_unsorted_gap_profile.zip"
    frame = pd.DataFrame(
        {"gc_close": [100.0, 100.2, 100.1]},
        index=pd.DatetimeIndex(
            pd.to_datetime(
                [
                    "2020-01-01T00:00:00Z",
                    "2020-01-01T00:00:05Z",
                    "2020-01-01T00:00:01Z",
                ]
            ),
            name="ts_event",
        ),
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc_1s/gc_1s_2020-01.parquet", _write_parquet(frame))

    payload = build_gc_fine_observed_gap_profile(
        zip_path,
        STRATEGY_PATH,
        created_at=CREATED_AT,
        top_n_gaps=3,
    ).to_payload()

    validate_gap_payload(payload)
    assert payload["periods"][0]["timestamp_order_status"] == "SORTED_FOR_PROFILE"
    assert payload["periods"][0]["largest_gap_seconds"] == 4
    assert payload["top_gaps"][0]["left_observed_at"] == "2020-01-01T00:00:01Z"
    assert payload["top_gaps"][0]["right_observed_at"] == "2020-01-01T00:00:05Z"

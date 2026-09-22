import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from trading_system.research.databento_gc_source_profile import build_databento_gc_source_profile

ROOT = Path(__file__).resolve().parents[2]
CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)
METADATA_PATH = ROOT / "configs/data/databento-gc-source-metadata.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
GC_COLUMNS = ["gc_open", "gc_high", "gc_low", "gc_close", "gc_volume"]


def _gc_frame(timestamps: list[str], *, tz: str | None = "UTC", bad_ohlc: bool = False) -> pd.DataFrame:
    index = pd.DatetimeIndex(pd.to_datetime(timestamps), name="ts_event")
    if tz is not None:
        index = index.tz_localize(tz) if index.tz is None else index.tz_convert(tz)
    high = 99.0 if bad_ohlc else 101.0
    return pd.DataFrame(
        {
            "gc_open": [100.0] * len(timestamps),
            "gc_high": [high] * len(timestamps),
            "gc_low": [99.0] * len(timestamps),
            "gc_close": [100.5] * len(timestamps),
            "gc_volume": [10.0] * len(timestamps),
        },
        index=index,
    )


def write_gc_zip(
    tmp_path: Path,
    *,
    columns: list[str] | None = None,
    tz: str | None = "UTC",
    bad_ohlc: bool = False,
) -> Path:
    frames = {
        "gc_2020-01.parquet": _gc_frame(
            ["2020-01-01T00:00:00", "2020-01-01T00:00:01"], tz=tz, bad_ohlc=bad_ohlc
        ),
        "gc_2020-02.parquet": _gc_frame(
            ["2020-02-01T00:00:00", "2020-02-01T00:00:01"], tz=tz, bad_ohlc=bad_ohlc
        ),
    }
    zip_path = tmp_path / "gc_test_archive.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, frame in frames.items():
            if columns is not None:
                frame = frame.copy()
                frame.columns = columns
            buffer = io.BytesIO()
            frame.to_parquet(buffer, engine="pyarrow")
            archive.writestr(name, buffer.getvalue())
    return zip_path


def validate_payload(payload: dict) -> None:
    schema = json.loads(
        (ROOT / "schemas/databento_gc_source_profile.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)


def profile(zip_path: Path, decisions_path: Path = DECISIONS_PATH) -> dict:
    return build_databento_gc_source_profile(
        zip_path,
        METADATA_PATH,
        decisions_path,
        created_at=CREATED_AT,
    ).to_payload()


def test_databento_gc_profile_reads_zip_metadata_without_leaking_path(tmp_path: Path):
    zip_path = write_gc_zip(tmp_path)
    payload = profile(zip_path)

    validate_payload(payload)
    assert payload["status"] == "PROFILE_SAMPLED_DATASET_BLOCKED"
    assert payload["zip_path"] == "LOCAL_PATH_REDACTED"
    assert payload["source_id"] == "databento-gc-1s"
    assert payload["canonical_symbol"] == "GC"
    assert payload["vendor"] == "DATABENTO"
    assert payload["parquet_entry_count"] == 2
    assert payload["columns"] == GC_COLUMNS
    assert payload["time_index_name"] == "ts_event"
    assert payload["time_index_timezone"] == "UTC"
    assert payload["row_count"] == 4
    assert payload["first_observed_at"] == "2020-01-01T00:00:00Z"
    assert payload["last_observed_at"] == "2020-02-01T00:00:01Z"
    assert payload["recommended_timeframe"] == "4h"
    assert payload["hhll_label_role"] == "AUXILIARY_DIRECTION_LABEL_ONLY"
    assert payload["hhll_files_not_in_scope"] is True
    assert payload["day_session_policy_status"] == "RESEARCH_DECISION_PENDING_MEASURE_FIRST"
    assert payload["production_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert payload["source_identity"]["status"] == "REAL_SOURCE_PENDING_HUMAN_DECISION"
    assert payload["source_identity"]["production_allowed"] is False
    assert payload["contract_identity_status"] == "UNDECLARED_PENDING_RESEARCH"
    assert payload["roll_policy_status"] == "RESEARCH_DECISION_PENDING"
    assert payload["ts_event_role"] == "INTERVAL_START_NOT_BAR_CLOSE"
    assert payload["no_trade_second_policy"] == "ABSENT_ROW_UNTIL_RESAMPLING_POLICY_DEFINED"
    assert payload["full_archive_quality_status"] == "NOT_PROVEN_IN_PHASE_20"
    for blocked_action in (
        "BUILD_REAL_DATASET",
        "DEPLOYMENT",
        "RUN_OFFLINE_DRY_RUN",
        "RESAMPLE_PERSISTENT_DATASET",
        "COPY_RAW_SOURCE",
        "MUTATE_RAW_SOURCE",
        "UPLOAD_RAW_SOURCE",
        "INGEST_HHLL_DERIVED_LABELS",
    ):
        assert blocked_action in payload["blocked_actions"]
    serialized = json.dumps(payload, sort_keys=True)
    assert str(zip_path) not in serialized
    assert "XAUUSD" not in serialized


def test_profile_blocks_on_unexpected_columns(tmp_path: Path):
    zip_path = write_gc_zip(
        tmp_path, columns=["open", "high", "low", "close", "volume"]
    )
    payload = profile(zip_path)

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "UNEXPECTED_COLUMNS" in payload["blocked_reasons"]


def test_profile_blocks_on_invalid_ohlc(tmp_path: Path):
    payload = profile(write_gc_zip(tmp_path, bad_ohlc=True))

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "INVALID_OHLC" in payload["blocked_reasons"]


def test_profile_blocks_on_naive_timestamp_index(tmp_path: Path):
    payload = profile(write_gc_zip(tmp_path, tz=None))

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "INDEX_NOT_TS_EVENT_UTC" in payload["blocked_reasons"]


def test_profile_blocks_on_missing_decisions_file(tmp_path: Path):
    payload = profile(write_gc_zip(tmp_path), decisions_path=tmp_path / "missing.yaml")

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "INVALID_DECISIONS_FILE" in payload["blocked_reasons"]


def test_profile_blocks_on_unreadable_zip(tmp_path: Path):
    payload = profile(tmp_path / "does_not_exist.zip")

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "UNREADABLE_ZIP" in payload["blocked_reasons"]


def test_gc_source_inventory_entry_stays_open_human_decision():
    import yaml

    inventory = yaml.safe_load((ROOT / "configs/data/source-inventory.yaml").read_text(encoding="utf-8"))
    gc_entries = [s for s in inventory["sources"] if s["source_id"] == "databento-gc-1s"]

    assert len(gc_entries) == 1
    assert gc_entries[0]["source_status"] == "OPEN_HUMAN_DECISION"
    assert gc_entries[0]["canonical_symbol"] == "GC"


def test_inspect_databento_gc_zip_cli_outputs_redacted_ready_json(tmp_path: Path):
    zip_path = write_gc_zip(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_databento_gc_zip.py",
            "--zip",
            str(zip_path),
            "--metadata",
            "configs/data/databento-gc-source-metadata.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "PROFILE_SAMPLED_DATASET_BLOCKED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(zip_path) not in result.stdout
    assert str(tmp_path) not in result.stdout

import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json
from trading_system.research.databento_gc_order_flow_profile import (
    build_databento_gc_order_flow_profile,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/databento_gc_order_flow_profile.schema.json"
METADATA_PATH = ROOT / "configs/data/databento-gc-order-flow-source-metadata.yaml"
GATES_PATH = ROOT / "configs/data/gc-order-flow-quality-gates.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CREATED_AT = datetime(2026, 9, 1, 16, 30, tzinfo=UTC)


def validate_order_flow_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _of_frame(include_cvd: bool = True) -> pd.DataFrame:
    index = pd.DatetimeIndex(
        pd.to_datetime(["2020-01-01T00:00:00Z", "2020-01-01T00:01:00Z"]),
        name="minute",
    )
    data = {
        "volume": [10, 20],
        "delta": [2, -3],
        "trades": [5, 7],
    }
    if include_cvd:
        data["cvd"] = [2, -1]
    return pd.DataFrame(data, index=index)


def _ohlcv_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        pd.to_datetime(["2020-01-01T00:00:00Z", "2020-01-01T00:01:00Z"]),
        name="minute",
    )
    return pd.DataFrame(
        {
            "open": [1500.0, 1501.0],
            "high": [1502.0, 1503.0],
            "low": [1499.0, 1500.5],
            "close": [1501.0, 1502.5],
            "volume": [10, 20],
        },
        index=index,
    )


def write_order_flow_zip(tmp_path: Path, *, include_readme: bool = True, include_ticks: bool = True) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_path / "gc_order_flow.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        if include_readme:
            archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(_of_frame(include_cvd=True)))
        archive.writestr("gc/GCext_of_1m.parquet", _parquet_bytes(_of_frame(include_cvd=False)))
        archive.writestr("gc/GCall_ohlcv_1m.parquet", _parquet_bytes(_ohlcv_frame()))
        if include_ticks:
            archive.writestr("gc/ticks/GC_trades_2020-01-01.dbn.zst", b"fake dbn zst bytes")
            archive.writestr("gc/ticks/GC_trades_2020-04-01.dbn.zst", b"fake dbn zst bytes")
    return zip_path


def minimal_valid_order_flow_payload() -> dict:
    return {
        "profile_id": "a" * 64,
        "profile_version": "databento-gc-order-flow-profile-0.1.0",
        "mode": "DATABENTO_GC_ORDER_FLOW_ZIP_PROFILE",
        "created_at": "2026-09-01T16:30:00Z",
        "status": "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED",
        "zip_path": "LOCAL_PATH_REDACTED",
        "zip_sha256": "b" * 64,
        "readme_present": True,
        "source_id": "databento-gc-order-flow",
        "vendor": "DATABENTO",
        "dataset": "GLBX.MDP3",
        "canonical_symbol": "GC",
        "raw_symbol": "GC",
        "order_flow_source_decision_status": "OPEN_HUMAN_DECISION",
        "options_source_decision_status": "DEFERRED_TO_V2_DO_NOT_QUERY",
        "parquet_files": ["gc/GCall_of_1m.parquet"],
        "dbn_zst_files": ["gc/ticks/GC_trades_2020-01-01.dbn.zst"],
        "sampled_parquet_count": 1,
        "parquet_entry_count": 1,
        "dbn_zst_entry_count": 1,
        "one_minute_order_flow_files": ["gc/GCall_of_1m.parquet"],
        "one_minute_ohlcv_files": [],
        "raw_tick_files": ["gc/ticks/GC_trades_2020-01-01.dbn.zst"],
        "columns_by_file": {"gc/GCall_of_1m.parquet": ["volume", "delta", "trades", "cvd", "minute"]},
        "timestamp_column_by_file": {"gc/GCall_of_1m.parquet": "minute"},
        "timezone_by_file": {"gc/GCall_of_1m.parquet": "UTC"},
        "row_count_by_file": {"gc/GCall_of_1m.parquet": 2},
        "range_by_file": {
            "gc/GCall_of_1m.parquet": {
                "start": "2020-01-01T00:00:00Z",
                "end": "2020-01-01T00:01:00Z",
            }
        },
        "known_damaged_aggressor_window": {
            "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
            "start": "2017-01-01T00:00:00Z",
            "end": "2017-06-01T00:00:00Z",
            "reason": "DAMAGED_AGGRESSOR_SIDE_DELTA",
        },
        "cumulative_feature_policy_status": "BLOCKED_PENDING_PIT_ERA_GAP_POLICY",
        "contract_identity_status": "UNDECLARED_PENDING_HUMAN_DECISION",
        "raw_tick_schema_family": "UNPROFILED_NAME_ONLY",
        "cumulative_column_status_by_file": {"gc/GCall_of_1m.parquet": "PRECOMPUTED_CUMULATIVE_UNSAFE"},
        "parquet_file_identity_status_by_file": {"gc/GCall_of_1m.parquet": "UNDECLARED_SESSION_OR_IDENTITY_VARIANT"},
        "reference_4h_csv_status": "REFERENCE_ONLY_DO_NOT_INGEST",
        "timeframe_status": "BASELINE_APPROVED_V1_NOT_MODEL_FINAL",
        "first_baseline_candidate": "30m_UTC_FIXED_BASELINE_APPROVED_V1",
        "macro_feature_status": "REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE",
        "production_allowed": False,
        "dataset_construction_allowed": False,
        "training_allowed": False,
        "allowed_next_actions": [],
        "blocked_actions": [
            "BUILD_ORDER_FLOW_FEATURES",
            "BUILD_REAL_DATASET",
            "TRAIN_PRODUCTION_MODEL",
            "USE_ARCHIVED_CVD_COLUMN",
            "INGEST_PRECOMPUTED_CVD",
            "INGEST_ORDERFLOW_4H_CSV",
            "JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS",
            "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
            "QUERY_OPTIONS_DATA",
            "JOIN_MACRO_FEATURES",
            "USE_REVISED_MACRO_SERIES",
            "MAP_GC_TO_XAUUSD",
            "MAP_GC_TO_GLD",
            "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
        ],
        "source_readiness_blockers": [
            "ORDER_FLOW_SOURCE_DECISION_OPEN",
            "CONTRACT_IDENTITY_UNDECLARED",
            "ERA_MAP_UNMEASURED",
            "PRECOMPUTED_CVD_COLUMN_UNSAFE",
        ],
        "blocked_reasons": [],
    }


def test_order_flow_configs_lock_profile_only_gates():
    metadata = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))
    gates = yaml.safe_load(GATES_PATH.read_text(encoding="utf-8"))

    assert metadata["source_id"] == "databento-gc-order-flow"
    assert metadata["source_status"] == "PROFILE_ONLY_NOT_SOURCE_APPROVED"
    assert metadata["canonical_symbol"] == "GC"
    assert metadata["vendor"] == "DATABENTO"
    assert "local_path" not in metadata

    assert gates["known_damaged_aggressor_window"]["start"] == "2017-01-01T00:00:00Z"
    assert gates["known_damaged_aggressor_window"]["end"] == "2017-06-01T00:00:00Z"
    assert gates["cumulative_features"]["status"] == "BLOCKED_PENDING_PIT_ERA_GAP_POLICY"
    assert gates["reference_4h_csv"]["status"] == "REFERENCE_ONLY_DO_NOT_INGEST"
    assert gates["timeframe"]["first_baseline_candidate"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1"
    assert gates["timeframe"]["status"] == "BASELINE_APPROVED_V1_NOT_MODEL_FINAL"
    assert "BAR_BOUNDARY" not in gates["timeframe"]["blocked_until_decided"]
    assert "TIMESTAMP_ROLE" not in gates["timeframe"]["blocked_until_decided"]
    assert gates["macro_features"]["status"] == "REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE"


def test_order_flow_profile_schema_accepts_profile_only_payload():
    payload = minimal_valid_order_flow_payload()
    validate_order_flow_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED"
    assert payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert "USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"]
    assert "MAP_GC_TO_XAUUSD" in payload["blocked_actions"]
    assert "PRECOMPUTED_CVD_COLUMN_UNSAFE" in payload["source_readiness_blockers"]


def test_order_flow_profile_reads_archive_shape_without_leaking_paths(tmp_path: Path):
    zip_path = write_order_flow_zip(tmp_path)
    profile = build_databento_gc_order_flow_profile(
        zip_path,
        METADATA_PATH,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    )
    payload = profile.to_payload()

    validate_order_flow_payload(payload)
    assert payload["zip_path"] == "LOCAL_PATH_REDACTED"
    assert payload["readme_present"] is True
    assert payload["parquet_entry_count"] == 3
    assert payload["dbn_zst_entry_count"] == 2
    assert payload["one_minute_order_flow_files"] == ["gc/GCall_of_1m.parquet", "gc/GCext_of_1m.parquet"]
    assert payload["one_minute_ohlcv_files"] == ["gc/GCall_ohlcv_1m.parquet"]
    assert payload["contract_identity_status"] == "UNDECLARED_PENDING_HUMAN_DECISION"
    assert payload["raw_tick_schema_family"] == "UNPROFILED_NAME_ONLY"
    assert payload["cumulative_column_status_by_file"]["gc/GCall_of_1m.parquet"] == "PRECOMPUTED_CUMULATIVE_UNSAFE"
    assert payload["timestamp_column_by_file"] == {
        "gc/GCall_of_1m.parquet": "minute",
        "gc/GCext_of_1m.parquet": "minute",
        "gc/GCall_ohlcv_1m.parquet": "minute",
    }
    assert payload["raw_tick_files"] == [
        "gc/ticks/GC_trades_2020-01-01.dbn.zst",
        "gc/ticks/GC_trades_2020-04-01.dbn.zst",
    ]
    assert payload["production_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_order_flow_profile_blocks_missing_readme_or_ticks(tmp_path: Path):
    no_readme_payload = build_databento_gc_order_flow_profile(
        write_order_flow_zip(tmp_path / "no_readme", include_readme=False),
        METADATA_PATH,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()
    assert no_readme_payload["status"] == "BLOCKED"
    assert "README_MISSING" in no_readme_payload["blocked_reasons"]

    no_ticks_payload = build_databento_gc_order_flow_profile(
        write_order_flow_zip(tmp_path / "no_ticks", include_ticks=False),
        METADATA_PATH,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()
    assert no_ticks_payload["status"] == "BLOCKED"
    assert "RAW_TICK_FILES_MISSING" in no_ticks_payload["blocked_reasons"]


def test_order_flow_profile_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_order_flow_zip(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_databento_gc_order_flow_zip.py",
            "--zip",
            str(zip_path),
            "--metadata",
            "configs/data/databento-gc-order-flow-source-metadata.yaml",
            "--gates",
            "configs/data/gc-order-flow-quality-gates.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_order_flow_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED"
    assert str(zip_path) not in result.stdout
    assert result.stderr == ""

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
SCHEMA_PATH = ROOT / "schemas/gc_order_flow_era_map.schema.json"
GATES_PATH = ROOT / "configs/data/gc-order-flow-quality-gates.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CREATED_AT = datetime(2026, 9, 1, 19, 0, tzinfo=UTC)


def validate_gc_order_flow_era_map_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _frame(columns: dict, *, tz_aware: bool = True) -> pd.DataFrame:
    timestamps = ["2020-01-01T00:00:00Z", "2020-01-01T00:01:00Z"]
    if tz_aware:
        minute = pd.to_datetime(timestamps)
    else:
        minute = pd.to_datetime(timestamps).tz_localize(None)
    return pd.DataFrame({**columns, "minute": minute})


def write_era_map_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_order_flow_era_map.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr(
            "gc/GCall_of_1m.parquet",
            _parquet_bytes(_frame({"volume": [10, 20], "delta": [2, -3], "trades": [5, 7], "cvd": [2, -1]})),
        )
        archive.writestr(
            "gc/GCext_of_1m.parquet",
            _parquet_bytes(_frame({"volume": [10, 20], "delta": [2, -3], "trades": [5, 7]}, tz_aware=False)),
        )
        archive.writestr(
            "gc/GCall_ohlcv_1m.parquet",
            _parquet_bytes(
                _frame({"open": [1.0, 2.0], "high": [2.0, 3.0], "low": [0.5, 1.5], "close": [1.5, 2.5], "volume": [10, 20]})
            ),
        )
    return zip_path


def minimal_valid_era_map_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-order-flow-era-map-0.1.0",
        "mode": "GC_ORDER_FLOW_ERA_MAP",
        "created_at": "2026-09-01T19:00:00Z",
        "status": "ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED",
        "zip_path": "LOCAL_PATH_REDACTED",
        "zip_sha256": "b" * 64,
        "canonical_symbol": "GC",
        "source_id": "databento-gc-order-flow",
        "interval_semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
        "order_flow_era_map_gate_status": "UNSATISFIED_FILE_CATALOG_ONLY",
        "cumulative_feature_policy_status": "BLOCKED_PENDING_PIT_FOLD_LOCAL_ERA_GAP_POLICY",
        "raw_tick_eras": "UNPROFILED_NAME_ONLY",
        "known_damaged_aggressor_window": {
            "start": "2017-01-01T00:00:00Z",
            "end": "2017-06-01T00:00:00Z",
            "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
            "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
        },
        "parquet_eras": [
            {
                "file": "gc/GCall_of_1m.parquet",
                "role": "ORDER_FLOW_1M",
                "columns": ["volume", "delta", "trades", "cvd", "minute"],
                "timestamp_column": "minute",
                "timezone_status": "UTC",
                "identity_status": "UNDECLARED_SESSION_OR_IDENTITY_VARIANT",
                "row_count": 2,
                "start": "2020-01-01T00:00:00Z",
                "end": "2020-01-01T00:01:00Z",
                "cvd_present": True,
                "cumulative_column_status": "PRECOMPUTED_CUMULATIVE_UNSAFE",
                "file_range_overlaps_known_damage": False,
            }
        ],
        "order_flow_source_decision_status": "OPEN_HUMAN_DECISION",
        "dataset_construction_allowed": False,
        "training_allowed": False,
        "allowed_next_actions": [],
        "blocked_actions": [
            "BUILD_ORDER_FLOW_FEATURES",
            "BUILD_REAL_DATASET",
            "BUILD_CVD_FEATURES",
            "USE_ARCHIVED_CVD_COLUMN",
            "INGEST_PRECOMPUTED_CVD",
            "BUILD_MACRO_FEATURES",
            "QUERY_OPTIONS_DATA",
            "INGEST_ORDERFLOW_4H_CSV",
            "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
            "MAP_GC_TO_XAUUSD",
            "MAP_GC_TO_GLD",
            "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
            "TRAIN_PRODUCTION_MODEL",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
        ],
        "source_readiness_blockers": [
            "ORDER_FLOW_SOURCE_DECISION_OPEN",
            "ORDER_FLOW_ERA_MAP_UNSATISFIED_FULL_AVAILABILITY_POLICY",
            "CANONICAL_ORDER_FLOW_INPUT_UNDECLARED",
            "CANONICAL_OHLCV_INPUT_UNDECLARED",
            "CUMULATIVE_FEATURE_POLICY_BLOCKED",
            "ROW_LEVEL_2017_MASK_UNIMPLEMENTED",
        ],
        "blocked_reasons": [],
    }


def test_gc_order_flow_era_map_schema_accepts_profiled_blocked_payload():
    payload = minimal_valid_era_map_payload()
    validate_gc_order_flow_era_map_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_FILE_CATALOG_ONLY"


def test_gc_order_flow_era_map_profiles_every_parquet_without_leaking_paths(tmp_path: Path):
    from trading_system.research.gc_order_flow_era_map import build_gc_order_flow_era_map

    zip_path = write_era_map_zip(tmp_path)
    payload = build_gc_order_flow_era_map(
        zip_path,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_gc_order_flow_era_map_payload(payload)
    eras = {entry["file"]: entry for entry in payload["parquet_eras"]}
    assert sorted(eras) == [
        "gc/GCall_of_1m.parquet",
        "gc/GCall_ohlcv_1m.parquet",
        "gc/GCext_of_1m.parquet",
    ]
    assert eras["gc/GCall_of_1m.parquet"]["role"] == "ORDER_FLOW_1M"
    assert eras["gc/GCall_of_1m.parquet"]["cvd_present"] is True
    assert eras["gc/GCall_of_1m.parquet"]["cumulative_column_status"] == "PRECOMPUTED_CUMULATIVE_UNSAFE"
    assert eras["gc/GCext_of_1m.parquet"]["timezone_status"] == "NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE"
    assert eras["gc/GCall_ohlcv_1m.parquet"]["role"] == "OHLCV_1M"
    assert eras["gc/GCall_ohlcv_1m.parquet"]["identity_status"] == "UNDECLARED_SESSION_OR_IDENTITY_VARIANT"
    assert payload["zip_path"] == "LOCAL_PATH_REDACTED"
    assert payload["allowed_next_actions"] == []
    assert payload["training_allowed"] is False
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_FILE_CATALOG_ONLY"
    assert "USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"]
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_gc_order_flow_era_map_marks_file_ending_at_damaged_start_as_overlap(tmp_path: Path):
    from trading_system.research.gc_order_flow_era_map import build_gc_order_flow_era_map

    zip_path = tmp_path / "gc_order_flow_era_map_boundary.zip"
    frame = pd.DataFrame(
        {
            "volume": [10],
            "delta": [2],
            "trades": [5],
            "minute": pd.to_datetime(["2017-01-01T00:00:00Z"]),
        }
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(frame))

    payload = build_gc_order_flow_era_map(
        zip_path,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    assert payload["parquet_eras"][0]["file_range_overlaps_known_damage"] is True


def test_gc_order_flow_era_map_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_era_map_zip(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_order_flow_era_map.py",
            "--zip",
            str(zip_path),
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
    validate_gc_order_flow_era_map_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED"
    assert len(payload["parquet_eras"]) == 3
    assert str(zip_path) not in result.stdout
    assert result.stderr == ""

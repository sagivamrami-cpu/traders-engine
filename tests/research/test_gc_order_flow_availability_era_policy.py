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
SCHEMA_PATH = ROOT / "schemas/gc_order_flow_availability_era_policy.schema.json"
GATES_PATH = ROOT / "configs/data/gc-order-flow-quality-gates.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CREATED_AT = datetime(2026, 9, 1, 21, 0, tzinfo=UTC)


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _policy_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "volume": [10, 20, 30, 40],
            "delta": [1, -2, 3, -4],
            "trades": [3, 4, 5, 6],
            "cvd": [1, -1, 2, -2],
            "minute": pd.to_datetime(
                [
                    "2016-12-31T23:59:00Z",
                    "2017-01-01T00:00:00Z",
                    "2017-06-01T00:00:00Z",
                    "2017-06-01T00:01:00Z",
                ]
            ),
        }
    )


def write_policy_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_order_flow_policy.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(_policy_frame()))
    return zip_path


def minimal_valid_policy_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-order-flow-availability-era-policy-0.1.0",
        "mode": "GC_ORDER_FLOW_AVAILABILITY_ERA_POLICY",
        "created_at": "2026-09-01T21:00:00Z",
        "status": "FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED",
        "policy_applies_to": "UNSELECTED_ZIP_MEMBERS",
        "zip_path": "LOCAL_PATH_REDACTED",
        "zip_sha256": "b" * 64,
        "canonical_symbol": "GC",
        "source_id": "databento-gc-order-flow",
        "policy_scope": "PARQUET_FILE_RANGE_REGIME_POLICY_ONLY",
        "order_flow_era_map_gate_status": "UNSATISFIED_POLICY_CANDIDATE_ONLY",
        "known_damaged_aggressor_window": {
            "start": "2017-01-01T00:00:00Z",
            "end": "2017-06-01T00:00:00Z",
            "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
            "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
        },
        "per_file_policies": [
            {
                "file": "gc/GCall_of_1m.parquet",
                "role": "ORDER_FLOW_1M",
                "identity_status": "UNDECLARED_SESSION_OR_IDENTITY_VARIANT",
                "timestamp_column": "minute",
                "timezone_status": "UTC",
                "range_start": "2016-12-31T23:59:00Z",
                "range_end": "2017-06-01T00:01:00Z",
                "cvd_present": True,
                "cumulative_column_status": "PRECOMPUTED_CUMULATIVE_UNSAFE",
                "allowed_for_training": False,
                "regimes": [
                    {
                        "regime_id": "PRE_KNOWN_DAMAGE_UNVERIFIED",
                        "semantics": "HALF_OPEN_UTC_ANNOTATION_ONLY_NOT_ROW_MASK",
                        "start": "2016-12-31T23:59:00Z",
                        "end": "2017-01-01T00:00:00Z",
                        "inclusion_status": "CANDIDATE_ONLY_REQUIRES_ROW_LEVEL_MASK",
                        "row_level_mask_status": "REQUIRED_NOT_IMPLEMENTED",
                        "cumulative_carry_status": "RESET_REQUIRED",
                    },
                    {
                        "regime_id": "KNOWN_DAMAGED_AGGRESSOR_WINDOW",
                        "semantics": "HALF_OPEN_UTC_ANNOTATION_ONLY_NOT_ROW_MASK",
                        "start": "2017-01-01T00:00:00Z",
                        "end": "2017-06-01T00:00:00Z",
                        "inclusion_status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
                        "row_level_mask_status": "REQUIRED_NOT_IMPLEMENTED",
                        "cumulative_carry_status": "RESET_REQUIRED",
                    },
                ],
            }
        ],
        "cumulative_boundary_policy": {
            "status": "BLOCKED_PENDING_IMPLEMENTATION",
            "reset_required_at": [
                "FILE_START",
                "KNOWN_DAMAGED_WINDOW_START",
                "KNOWN_DAMAGED_WINDOW_END",
                "WALK_FORWARD_FOLD_BOUNDARY",
            ],
            "forbidden_carry_features": ["CVD", "CUMULATIVE_DELTA"],
            "archived_cvd_use": "FORBIDDEN",
        },
        "dataset_construction_allowed": False,
        "training_allowed": False,
        "allowed_next_actions": [],
        "blocked_actions": [
            "BUILD_REAL_DATASET",
            "BUILD_ORDER_FLOW_FEATURES",
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
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
        ],
        "required_remaining_gates": [
            "ORDER_FLOW_ERA_MAP",
            "ORDER_FLOW_SOURCE_DECISION",
            "CANONICAL_ORDER_FLOW_INPUT",
            "CANONICAL_OHLCV_INPUT",
            "ROW_LEVEL_2017_MASK",
            "CUMULATIVE_FEATURE_POLICY",
            "DATASET_CONSTRUCTION_AUTHORIZATION",
        ],
        "blocked_reasons": [],
    }


def test_gc_order_flow_availability_policy_schema_accepts_blocked_candidate_payload():
    payload = minimal_valid_policy_payload()
    validate_policy_payload(payload)
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_CANDIDATE_ONLY"
    assert "ORDER_FLOW_ERA_MAP" in payload["required_remaining_gates"]
    assert payload["policy_applies_to"] == "UNSELECTED_ZIP_MEMBERS"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False


def test_gc_order_flow_availability_policy_splits_known_damage_regimes_and_blocks_training(tmp_path: Path):
    from trading_system.research.gc_order_flow_availability_era_policy import (
        build_gc_order_flow_availability_era_policy,
    )

    zip_path = write_policy_zip(tmp_path)
    payload = build_gc_order_flow_availability_era_policy(
        zip_path,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    policy = payload["per_file_policies"][0]
    assert [regime["regime_id"] for regime in policy["regimes"]] == [
        "PRE_KNOWN_DAMAGE_UNVERIFIED",
        "KNOWN_DAMAGED_AGGRESSOR_WINDOW",
        "POST_KNOWN_DAMAGE_REQUIRES_PIT_RECOMPUTE",
    ]
    assert {regime["semantics"] for regime in policy["regimes"]} == {
        "HALF_OPEN_UTC_ANNOTATION_ONLY_NOT_ROW_MASK"
    }
    assert {regime["row_level_mask_status"] for regime in policy["regimes"]} == {
        "REQUIRED_NOT_IMPLEMENTED"
    }
    assert policy["allowed_for_training"] is False
    assert policy["cumulative_column_status"] == "PRECOMPUTED_CUMULATIVE_UNSAFE"
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_CANDIDATE_ONLY"
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)


def test_gc_order_flow_availability_policy_does_not_apply_aggressor_damage_to_ohlcv(tmp_path: Path):
    from trading_system.research.gc_order_flow_availability_era_policy import (
        build_gc_order_flow_availability_era_policy,
    )

    zip_path = tmp_path / "gc_order_flow_policy_with_ohlcv.zip"
    ohlcv = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [2.0, 3.0],
            "low": [0.5, 1.5],
            "close": [1.5, 2.5],
            "volume": [10, 20],
            "minute": pd.to_datetime(["2017-01-01T00:00:00Z", "2017-06-01T00:00:00Z"]),
        }
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(_policy_frame()))
        archive.writestr("gc/GCall_ohlcv_1m.parquet", _parquet_bytes(ohlcv))

    payload = build_gc_order_flow_availability_era_policy(
        zip_path,
        GATES_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    policies = {policy["file"]: policy for policy in payload["per_file_policies"]}
    ohlcv_policy = policies["gc/GCall_ohlcv_1m.parquet"]
    assert [regime["regime_id"] for regime in ohlcv_policy["regimes"]] == [
        "OHLCV_NOT_SUBJECT_TO_AGGRESSOR_DAMAGE_WITHOUT_SEPARATE_DECISION"
    ]
    assert ohlcv_policy["regimes"][0]["inclusion_status"] == (
        "OHLCV_NOT_SUBJECT_TO_AGGRESSOR_DAMAGE_WITHOUT_SEPARATE_DECISION"
    )


def test_gc_order_flow_availability_policy_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_policy_zip(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_gc_order_flow_availability_era_policy.py",
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
    validate_policy_payload(payload)
    assert payload["status"] == "FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED"
    assert payload["dataset_construction_allowed"] is False
    assert str(zip_path) not in result.stdout
    assert result.stderr == ""

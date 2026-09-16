import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_order_flow_row_mask_cumulative_policy.schema.json"
CREATED_AT = datetime(2026, 9, 2, 5, 0, tzinfo=UTC)


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_order_flow_row_mask_policy_applies_half_open_2017_exclusion():
    from trading_system.research.gc_order_flow_row_mask_cumulative_policy import (
        apply_gc_order_flow_training_mask,
    )

    frame = pd.DataFrame(
        {
            "minute": pd.to_datetime(
                [
                    "2016-12-31T23:59:00Z",
                    "2017-01-01T00:00:00Z",
                    "2017-05-31T23:59:00Z",
                    "2017-06-01T00:00:00Z",
                    "2017-06-01T00:01:00Z",
                ]
            )
        }
    )

    mask = apply_gc_order_flow_training_mask(frame["minute"])

    assert mask.tolist() == [True, False, False, True, True]


def test_gc_order_flow_row_mask_policy_localizes_naive_minutes_as_utc_wall_clock():
    from trading_system.research.gc_order_flow_row_mask_cumulative_policy import (
        apply_gc_order_flow_training_mask,
    )

    minutes = pd.Series(
        pd.to_datetime(
            [
                "2016-12-31 23:59:00",
                "2017-01-01 00:00:00",
                "2017-06-01 00:00:00",
            ]
        )
    )

    mask = apply_gc_order_flow_training_mask(minutes)

    assert mask.tolist() == [True, False, True]


def test_gc_order_flow_row_mask_cumulative_policy_satisfies_era_and_cumulative_policy_only():
    from trading_system.research.gc_order_flow_row_mask_cumulative_policy import (
        build_gc_order_flow_row_mask_cumulative_policy_report,
    )

    payload = build_gc_order_flow_row_mask_cumulative_policy_report(
        POLICY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    assert payload["status"] == "ORDER_FLOW_ROW_MASK_AND_CUMULATIVE_POLICY_RECORDED"
    assert payload["canonical_symbol"] == "GC"
    assert payload["selected_member"] == "gc/GCext_of_1m.parquet"
    assert payload["mask_predicate"] == "minute < damaged_start OR minute >= damaged_end"
    assert payload["known_damaged_aggressor_window"]["start"] == "2017-01-01T00:00:00Z"
    assert payload["known_damaged_aggressor_window"]["end"] == "2017-06-01T00:00:00Z"
    assert payload["order_flow_era_map_gate_status"] == "SATISFIED_ROW_LEVEL_MASK_POLICY_ONLY"
    assert payload["cumulative_feature_policy_status"] == "SATISFIED_NO_CVD_OR_CUMULATIVE_CARRY_V1"
    assert payload["archived_cvd_policy"] == "FORBIDDEN"
    assert payload["allowed_order_flow_feature_columns"] == ["volume", "delta", "trades"]
    assert payload["forbidden_order_flow_feature_columns"] == ["cvd", "cumulative_delta"]
    assert payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False


def test_gc_order_flow_row_mask_cumulative_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_order_flow_row_mask_cumulative_policy.py",
            "--policy",
            "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_policy_payload(payload)
    assert payload["order_flow_era_map_gate_status"] == "SATISFIED_ROW_LEVEL_MASK_POLICY_ONLY"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

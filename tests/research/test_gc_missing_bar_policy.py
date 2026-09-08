import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/gc-missing-bar-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_missing_bar_policy.schema.json"
CREATED_AT = datetime(2026, 9, 2, 14, 0, tzinfo=UTC)


def validate_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_missing_bar_policy_is_satisfied_fail_closed_and_matches_builder():
    from trading_system.research.gc_missing_bar_policy import build_gc_missing_bar_policy_report

    payload = build_gc_missing_bar_policy_report(POLICY_PATH, created_at=CREATED_AT).to_payload()
    validate_payload(payload)
    assert payload["status"] == "MISSING_BAR_POLICY_IMPLEMENTED_FAIL_CLOSED_V1"
    assert payload["missing_bar_policy_gate_status"] == "SATISFIED_FAIL_CLOSED_EXCLUSION_V1"
    assert payload["builder_constants_match"] is True
    assert payload["blocked_reasons"] == []
    assert payload["fill_policy"] == "NO_FORWARD_FILL_NO_INVENTED_VALUES"
    assert payload["order_flow_optional_variant_allowed"] is False
    assert payload["family_status"]["order_flow_cvd_family"] == "FORBIDDEN_NOT_A_FEATURE_FAMILY"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert "MISSING_EXPECTED_BAR_COUNTS_BY_TRADE_DATE" in payload["manifest_requirements"]
    assert payload["calendar_scope_decision_ref"].endswith("session-calendar-v1-scope-overlay-transfer.md")


def test_missing_bar_policy_rejects_builder_drift(tmp_path: Path):
    from trading_system.research.gc_missing_bar_policy import build_gc_missing_bar_policy_report

    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    policy["feature_lookback_bars"] = 10
    policy["exclusion_reasons_order_flow_variant"] = ["ORDER_FLOW_OUTSIDE_COVERAGE"]
    drifted = tmp_path / "policy.yaml"
    drifted.write_text(yaml.safe_dump(policy), encoding="utf-8")

    report = build_gc_missing_bar_policy_report(drifted, created_at=CREATED_AT)
    assert "FEATURE_LOOKBACK_BARS_MISMATCH" in report.payload["blocked_reasons"]
    assert "ORDER_FLOW_VARIANT_REASONS_MISMATCH" in report.payload["blocked_reasons"]
    assert report.payload["builder_constants_match"] is False
    with pytest.raises(Exception):
        report.to_payload()


def test_missing_bar_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [sys.executable, "tools/validate_gc_missing_bar_policy.py", "--policy", "configs/data/gc-missing-bar-policy.yaml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["missing_bar_policy_gate_status"] == "SATISFIED_FAIL_CLOSED_EXCLUSION_V1"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

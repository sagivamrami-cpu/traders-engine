import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/gc-session-calendar-overlay-reconciliation-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_calendar_overlay_reconciliation_policy.schema.json"
CREATED_AT = datetime(2026, 9, 2, 2, 30, tzinfo=UTC)


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_calendar_overlay_reconciliation_policy_is_fail_closed():
    from trading_system.research.gc_calendar_overlay_reconciliation_policy import (
        build_gc_calendar_overlay_reconciliation_policy_report,
    )

    payload = build_gc_calendar_overlay_reconciliation_policy_report(
        POLICY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    assert payload["status"] == "OVERLAY_RECONCILIATION_POLICY_CANDIDATE_REQUIRES_EVIDENCE"
    assert payload["session_calendar_gate_status"] == "UNSATISFIED_OVERLAY_RECONCILIATION_POLICY_ONLY"
    assert payload["observed_gap_profile_status"] == "BOUNDED_SMOKE_ONLY_FULL_PROFILE_PENDING"
    assert payload["overlay_table_status"] == "REQUIRED_NOT_IMPLEMENTED"
    assert payload["reconciliation_table_status"] == "REQUIRED_NOT_IMPLEMENTED"
    assert "HOLIDAY" in payload["required_overlay_types"]
    assert "SPECIAL_HOURS" in payload["required_overlay_types"]
    assert "VENUE_HALT" in payload["required_overlay_types"]
    assert "SOURCE_ATTRIBUTION_PER_OVERLAY" in payload["required_reconciliation_controls"]
    assert payload["calendar_registration_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False


def test_gc_calendar_overlay_reconciliation_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_calendar_overlay_reconciliation_policy.py",
            "--policy",
            "configs/data/gc-session-calendar-overlay-reconciliation-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_policy_payload(payload)
    assert payload["status"] == "OVERLAY_RECONCILIATION_POLICY_CANDIDATE_REQUIRES_EVIDENCE"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

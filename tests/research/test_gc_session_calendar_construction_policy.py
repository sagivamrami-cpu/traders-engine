import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/gc-session-calendar-construction-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_construction_policy.schema.json"
SESSION_CALENDAR_PATH = ROOT / "configs/data/session-calendar.yaml"
CREATED_AT = datetime(2026, 9, 2, 0, 30, tzinfo=UTC)
PENDING_GC_METALS_CALENDAR_ID = "cme-globex-metals-research-pending-v1"
GC_METALS_CALENDAR_ID = "cme-globex-metals-research-v1"


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_session_calendar_construction_policy_registers_research_calendar_without_training():
    from trading_system.research.gc_session_calendar_construction_policy import (
        build_gc_session_calendar_construction_policy_report,
    )

    payload = build_gc_session_calendar_construction_policy_report(
        POLICY_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    assert payload["calendar_id"] == GC_METALS_CALENDAR_ID
    assert payload["status"] == "RESEARCH_CALENDAR_REGISTERED_V1_NOT_EXECUTION_TRUTH"
    assert payload["session_calendar_gate_status"] == "SATISFIED_RESEARCH_CALENDAR_V1"
    assert payload["calendar_registration_allowed"] is True
    assert payload["construction_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["registered_calendar_ref"] == "configs/data/session-calendar.yaml#cme-globex-metals-research-v1"
    assert payload["implementation_decision_ref"].endswith("human-d2-final-session-calendar-implementation.md")
    assert payload["databento_status_skip_decision_ref"].endswith(
        "human-d2-final-databento-status-schema-skip.md"
    )
    assert payload["scope_amendment_decision_ref"].endswith(
        "human-d2-final-session-calendar-v1-scope-overlay-transfer.md"
    )
    assert payload["normal_session_template"]["timezone"] == "America/Chicago"
    assert payload["normal_session_template"]["template_status"] == "REGISTERED_RESEARCH_NORMAL_HOURS_V1"
    assert payload["normal_session_template"]["open_time_ct"] == "17:00"
    assert payload["normal_session_template"]["close_time_ct"] == "16:00"
    assert payload["era_versioning"]["required"] is True
    assert payload["era_versioning"]["guessed_membership_allowed"] is False
    assert "HOLIDAYS" in payload["overlay_requirements"]
    assert "SPECIAL_HOURS" in payload["overlay_requirements"]
    assert "SOURCE_ATTRIBUTION_PER_DATE_OR_ERA" in payload["reconciliation_requirements"]
    assert payload["bar_membership_rules"]["rule_status"] == "IMPLEMENTED_RESEARCH_V1"
    assert "REGISTER_SESSION_CALENDAR" not in payload["blocked_actions"]
    assert "QUERY_DATABENTO_STATUS_SCHEMA" in payload["blocked_actions"]


def test_phase32_rejects_pending_gc_calendar_registration(tmp_path: Path):
    from tools.validate_phase31 import assert_pending_gc_metals_calendar_absent

    calendar_path = tmp_path / "session-calendar.yaml"
    calendar_path.write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "calendars": {
                    "us-equities-regular-v1": {},
                    PENDING_GC_METALS_CALENDAR_ID: {},
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
        raise AssertionError("Phase 32 must reject pending GC calendar registration")


def test_phase32_current_session_calendar_has_no_gc_metals_registration():
    calendar = yaml.safe_load(SESSION_CALENDAR_PATH.read_text(encoding="utf-8"))
    assert PENDING_GC_METALS_CALENDAR_ID not in set(calendar.get("calendars", {}))
    assert GC_METALS_CALENDAR_ID in set(calendar.get("calendars", {}))


def test_gc_session_calendar_construction_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_session_calendar_construction_policy.py",
            "--policy",
            "configs/data/gc-session-calendar-construction-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_policy_payload(payload)
    assert payload["status"] == "RESEARCH_CALENDAR_REGISTERED_V1_NOT_EXECUTION_TRUTH"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

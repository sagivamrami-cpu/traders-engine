from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json

SCHEMA_PATH = ROOT / "schemas/gc_bar_session_timestamp_policy.schema.json"
POLICY_PATH = ROOT / "configs/data/gc-bar-session-timestamp-policy.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase27.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_bar_session_timestamp_policy.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_bar_session_timestamp_policy.py"),
            "--policy",
            str(POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    # Retargeted after Phases 43-45 (missing-bar policy resolved, construction authorized).
    _require(
        payload["status"] == "POLICY_APPROVED_MISSING_BAR_RESOLVED_CONSTRUCTION_AUTHORIZED",
        "policy must reflect resolved missing-bar policy and authorized construction",
    )
    _require(payload["dataset_construction_allowed"] is True, "identified dataset construction must be authorized")
    _require(payload["resampling_allowed"] is True, "resampling for the identified build must be allowed")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    _require(
        payload["candidate_timeframe"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1",
        "30m UTC-fixed baseline must reflect D1 approval",
    )
    _require(
        payload["bar_boundary_policy"]["available_at"] == "BAR_END_UTC_APPROVED_V1",
        "available_at must reflect D1 approval",
    )
    _require(
        payload["session_calendar_policy"]["calendar_id"] == "cme-globex-metals-research-v1",
        "calendar id must be the registered research v1 calendar",
    )
    _require(
        payload["session_calendar_policy"]["status"]
        == "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH",
        "session calendar must reflect D2 final research implementation",
    )
    _require(
        payload["session_calendar_policy"]["decision_ref"]
        == "agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md",
        "session-calendar policy must point to the D2 final implementation decision record",
    )
    _require(
        payload["session_calendar_policy"]["holiday_overlay_status"]
        == "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1",
        "holiday overlay must be transferred to the missing-bar policy",
    )
    _require(
        payload["session_calendar_policy"]["open_reconciliation_questions"] == [],
        "reconciliation questions must be answered",
    )
    _require(
        payload["session_calendar_policy"]["utc_bar_session_membership_status"] == "IMPLEMENTED_RESEARCH_V1",
        "UTC/CT session membership must be encoded for research v1",
    )
    _require(
        payload["timestamp_policy"]["status"] == "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED",
        "timestamp policy must carry human v1 approval without dataset authorization",
    )
    _require(
        payload["timestamp_policy"]["decision_ref"]
        == "agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md",
        "timestamp policy must point to the D3 decision record",
    )
    _require(payload["required_remaining_gates"] == [], "no gate may remain on the timestamp policy")
    _require("MISSING_BAR_POLICY" not in payload["required_remaining_gates"], "MISSING_BAR_POLICY should be resolved by Phase 43")
    _require("SESSION_CALENDAR" not in payload["required_remaining_gates"], "SESSION_CALENDAR should be resolved by D2 final")
    _require("TIMESTAMP_ROLE" not in payload["required_remaining_gates"], "TIMESTAMP_ROLE should be resolved by D3")
    _require("BAR_BOUNDARY" not in payload["required_remaining_gates"], "BAR_BOUNDARY should be resolved by D1")
    _require("AVAILABLE_AT_POLICY" not in payload["required_remaining_gates"], "AVAILABLE_AT_POLICY should be resolved by D1")
    _require("RESAMPLE_REAL_BARS" not in payload["blocked_actions"], "resampling must not be blocked once authorized")
    for action in (
        "CLAIM_EDGE",
        "USE_ARCHIVED_CVD_COLUMN",
        "MAP_GC_TO_XAUUSD",
        "INGEST_ORDERFLOW_4H_CSV",
        "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
    ):
        _require(action in payload["blocked_actions"], f"blocked action missing: {action}")
    _require(payload["blocked_reasons"] == [], "no blocked reason may remain on the timestamp policy")
    for closed_reason in (
        "MISSING_BAR_POLICY_GATE_UNSATISFIED",
        "SESSION_CALENDAR_GATE_UNSATISFIED",
        "HOLIDAY_OVERLAY_REQUIRED_NOT_ENCODED",
        "UTC_BAR_SESSION_MEMBERSHIP_REQUIRED_NOT_ENCODED",
    ):
        _require(closed_reason not in payload["blocked_reasons"], f"closed reason still present: {closed_reason}")
    _require(
        "TIMESTAMP_ROLE_GATE_UNSATISFIED" not in payload["blocked_reasons"],
        "timestamp blocker should be removed after D3",
    )
    _require(
        "BAR_BOUNDARY_GATE_UNSATISFIED" not in payload["blocked_reasons"],
        "bar-boundary blocker should be removed after D1",
    )
    _require(
        "AVAILABLE_AT_POLICY_GATE_UNSATISFIED" not in payload["blocked_reasons"],
        "available-at blocker should be removed after D1",
    )
    for forbidden in (str(POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "bar/session/timestamp policy output must not include local paths")
    print("Phase 28 artifacts validated")


if __name__ == "__main__":
    main()

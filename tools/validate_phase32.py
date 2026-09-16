from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from tools.validate_phase31 import assert_pending_gc_metals_calendar_absent

SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_construction_policy.schema.json"
POLICY_PATH = ROOT / "configs/data/gc-session-calendar-construction-policy.yaml"
SESSION_CALENDAR_PATH = ROOT / "configs/data/session-calendar.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    assert_pending_gc_metals_calendar_absent(SESSION_CALENDAR_PATH)
    _run([sys.executable, str(ROOT / "tools/validate_phase31.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_session_calendar_construction_policy.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_session_calendar_construction_policy.py"),
            "--policy",
            str(POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    validate_json_payload(SCHEMA_PATH, payload)
    _require(
        payload["status"] == "RESEARCH_CALENDAR_REGISTERED_V1_NOT_EXECUTION_TRUTH",
        "construction policy must register the research calendar",
    )
    _require(
        payload["session_calendar_gate_status"] == "SATISFIED_RESEARCH_CALENDAR_V1",
        "construction policy must satisfy the research session-calendar gate",
    )
    _require(payload["calendar_registration_allowed"] is True, "calendar registration must be allowed")
    _require(
        payload["registered_calendar_ref"] == "configs/data/session-calendar.yaml#cme-globex-metals-research-v1",
        "registered calendar ref must point at the GC research calendar",
    )
    for key in ("construction_allowed", "dataset_construction_allowed", "resampling_allowed", "training_allowed"):
        _require(payload[key] is False, f"{key} must remain false")
    _require("REGISTER_SESSION_CALENDAR" not in payload["blocked_actions"], "calendar registration must not remain blocked")
    for action in (
        "RESAMPLE_REAL_BARS",
        "BUILD_REAL_DATASET",
        "QUERY_DATABENTO_STATUS_SCHEMA",
        "TRAIN_PRODUCTION_MODEL",
    ):
        _require(action in payload["blocked_actions"], f"blocked action missing: {action}")
    for forbidden in (str(POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "construction policy output must not include local paths")
    print("Phase 32 artifacts validated")


if __name__ == "__main__":
    main()

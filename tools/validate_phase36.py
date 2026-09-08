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

SCHEMA_PATH = ROOT / "schemas/gc_calendar_overlay_reconciliation_policy.schema.json"
POLICY_PATH = ROOT / "configs/data/gc-session-calendar-overlay-reconciliation-policy.yaml"
SESSION_CALENDAR_PATH = ROOT / "configs/data/session-calendar.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    assert_pending_gc_metals_calendar_absent(SESSION_CALENDAR_PATH)
    _run([sys.executable, str(ROOT / "tools/validate_phase35.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_calendar_overlay_reconciliation_policy.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_calendar_overlay_reconciliation_policy.py"),
            "--policy",
            str(POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    validate_json_payload(SCHEMA_PATH, payload)
    _require(
        payload["status"] == "OVERLAY_RECONCILIATION_POLICY_CANDIDATE_REQUIRES_EVIDENCE",
        "overlay/reconciliation policy must remain evidence-gated",
    )
    _require(payload["overlay_table_status"] == "REQUIRED_NOT_IMPLEMENTED", "overlay table must remain unimplemented")
    _require(
        payload["reconciliation_table_status"] == "REQUIRED_NOT_IMPLEMENTED",
        "reconciliation table must remain unimplemented",
    )
    _require(payload["calendar_registration_allowed"] is False, "calendar registration must remain blocked")
    _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
    _require(payload["resampling_allowed"] is False, "resampling must remain blocked")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    for forbidden in (str(POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "overlay/reconciliation policy output must not include local paths")
    print("Phase 36 artifacts validated")


if __name__ == "__main__":
    main()

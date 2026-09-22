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

SCHEMA_PATH = ROOT / "schemas/gc_real_dataset_contract.schema.json"
CONTRACT_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=check)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase23.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_real_dataset_contract.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    contract_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_real_dataset_contract.py"),
            "--contract",
            str(CONTRACT_PATH),
            "--decisions",
            str(DECISIONS_PATH),
        ]
    )
    payload = json.loads(contract_result.stdout)
    # Retargeted after Phases 43-45: one identified dataset build is authorized
    # (D9-final record bound to dataset_id); training stays blocked.
    _require(
        payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED",
        "GC real-dataset contract must be construction-authorized with training blocked",
    )
    _require(
        payload["missing_bar_policy"]["status"] == "SATISFIED_FAIL_CLOSED_EXCLUSION_V1",
        "missing-bar policy must be satisfied fail-closed",
    )
    _require(
        payload["dataset_identity"]["status"] == "SATISFIED_DETERMINISTIC_IDENTITY_V1",
        "dataset identity must be satisfied",
    )
    _require(len(payload["dataset_identity"]["dataset_id"]) == 64, "dataset identity must carry a dataset_id")
    _require(
        payload["session_calendar"]["status"] == "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH",
        "session calendar must be satisfied for research only",
    )
    _require(
        payload["session_calendar"]["decision_ref"]
        == "agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md",
        "session calendar must point to the D2 final implementation decision record",
    )
    _require(
        payload["session_calendar"]["construction_policy_ref"]
        == "configs/data/gc-session-calendar-construction-policy.yaml",
        "session calendar must point to the construction policy",
    )
    _require(
        payload["session_calendar"]["calendar_id"] == "cme-globex-metals-research-v1",
        "session calendar id must be the registered research v1 calendar",
    )
    _require(
        payload["available_at_policy"]["non_closed_bar_feature_policy"]
        == "UNDEFINED_BLOCKED_PENDING_NEW_HUMAN_DECISION",
        "non-closed-bar features must remain outside D1 available-at approval",
    )
    _require(payload["dataset_construction_allowed"] is True, "one identified dataset build must be authorized")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    _require(len(payload["construction_authorized_by"]) >= 1, "construction authorization record must be recorded")
    for ref in payload["construction_authorized_by"]:
        _require(ref.startswith("agent-exchange/decisions/"), "authorization must be a human decision record")
        record = (ROOT / ref).read_text(encoding="utf-8")
        _require("Decision: APPROVED" in record, "authorization record must be approved")
        _require(payload["dataset_identity"]["dataset_id"] in record, "authorization record must bind dataset_id")
    _require(payload["allowed_next_actions"] == ["BUILD_IDENTIFIED_REAL_DATASET"], "only the identified build is allowed")
    _require(payload["blocked_reasons"] == [], "no blocker may remain on the authorized contract")

    required_gates = set(payload["required_unsatisfied_gates"])
    _require(not required_gates, f"no gate may remain unsatisfied: {sorted(required_gates)}")

    blocked_actions = set(payload["blocked_actions"])
    _require("BUILD_REAL_DATASET" not in blocked_actions, "the identified build must not be listed as blocked")
    for action in (
        "BUILD_CVD_FEATURES",
        "QUERY_OPTIONS_DATA",
        "INGEST_ORDERFLOW_4H_CSV",
        "TRAIN_PRODUCTION_MODEL",
    ):
        _require(action in blocked_actions, f"blocked action missing: {action}")

    for forbidden in (str(CONTRACT_PATH), str(DECISIONS_PATH), "C:\\", "/Users/"):
        _require(forbidden not in contract_result.stdout, "contract CLI output must not include local paths")

    readiness_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/real_data_readiness.py"),
            "--decisions",
            str(DECISIONS_PATH),
        ]
    )
    readiness = json.loads(readiness_result.stdout)
    _require(readiness["status"] == "BLOCKED", "real-data readiness must remain blocked")
    _require(readiness["satisfied_count"] == 6, "readiness must satisfy exactly six items")
    _require(readiness["open_count"] == 1, "only options readiness item must remain open/deferred")

    print("Phase 24 artifacts validated")


if __name__ == "__main__":
    main()

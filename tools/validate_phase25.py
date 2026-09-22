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

SCHEMA_PATH = ROOT / "schemas/gc_pretraining_readiness_report.schema.json"
CONTRACT_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CHECKLIST_PATH = ROOT / "configs/research/real-data-readiness-checklist.yaml"
TRAINING_POLICY_PATH = ROOT / "configs/models/baseline-training-policy.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase24.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_pretraining_readiness.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/gc_pretraining_readiness.py"),
            "--contract",
            str(CONTRACT_PATH),
            "--decisions",
            str(DECISIONS_PATH),
            "--checklist",
            str(CHECKLIST_PATH),
            "--training-policy",
            str(TRAINING_POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    # Retargeted after Phases 43-45: construction of the identified dataset is
    # authorized; without a build manifest the report must still be BLOCKED on
    # REAL_DATASET_NOT_BUILT and training must not start.
    _require(payload["status"] == "BLOCKED", "pre-training readiness without a build must remain blocked")
    _require(payload["training_start_allowed"] is False, "training start must remain blocked without a build")
    _require(payload["dataset_construction_allowed"] is True, "identified dataset construction must be authorized")
    _require(payload["model_promotion_allowed"] is False, "model promotion must remain blocked")
    _require(
        payload["dataset_contract_status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED",
        "contract status must be construction-authorized with training blocked",
    )
    required_gates = set(payload["required_pretraining_gates"])
    _require("REAL_DATASET_NOT_BUILT" in required_gates, "REAL_DATASET_NOT_BUILT must gate without a build")
    for closed_gate in (
        "SESSION_CALENDAR",
        "MISSING_BAR_POLICY",
        "DATASET_IDENTITY",
        "DATASET_CONSTRUCTION_AUTHORIZATION",
        "ORDER_FLOW_SOURCE_DECISION",
        "ORDER_FLOW_ERA_MAP",
        "CUMULATIVE_FEATURE_POLICY",
        "LABEL_CONTRACT",
        "SPLIT_AND_EMBARGO_POLICY",
    ):
        _require(closed_gate not in required_gates, f"closed gate still present: {closed_gate}")
    _require("BUILD_IDENTIFIED_REAL_DATASET" in payload["pending_process_steps"], "build must be the pending step")
    _require("TRAIN_PRODUCTION_MODEL" in payload["blocked_actions"], "production training must stay blocked")
    for forbidden in (str(CONTRACT_PATH), str(DECISIONS_PATH), str(CHECKLIST_PATH), str(TRAINING_POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "pre-training readiness output must not include local paths")
    print("Phase 25 artifacts validated")


if __name__ == "__main__":
    main()

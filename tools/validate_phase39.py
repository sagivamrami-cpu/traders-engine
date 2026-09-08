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

SCHEMA_PATH = ROOT / "schemas/gc_order_flow_row_mask_cumulative_policy.schema.json"
POLICY_PATH = ROOT / "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_order_flow_row_mask_cumulative_policy.py", "-q"])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_real_dataset_contract.py", "-q"])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_pretraining_readiness.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_order_flow_row_mask_cumulative_policy.py"),
            "--policy",
            str(POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    validate_json_payload(SCHEMA_PATH, payload)
    _require(
        payload["order_flow_era_map_gate_status"] == "SATISFIED_ROW_LEVEL_MASK_POLICY_ONLY",
        "order-flow era map must be satisfied only by row-level mask policy",
    )
    _require(
        payload["cumulative_feature_policy_status"] == "SATISFIED_NO_CVD_OR_CUMULATIVE_CARRY_V1",
        "cumulative policy must forbid CVD/cumulative carry in v1",
    )
    _require(
        payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION",
        "order-flow source decision must remain open",
    )
    _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    for forbidden in (str(POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "row-mask/cumulative policy output must not include local paths")
    print("Phase 39 artifacts validated")


if __name__ == "__main__":
    main()

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

SCHEMA_PATH = ROOT / "schemas/gc_canonical_order_flow_input_manifest.schema.json"
MANIFEST_PATH = ROOT / "configs/data/gc-canonical-order-flow-input-manifest.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_canonical_order_flow_input_manifest.py", "-q"])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_real_dataset_contract.py", "-q"])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_pretraining_readiness.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_canonical_order_flow_input_manifest.py"),
            "--manifest",
            str(MANIFEST_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    validate_json_payload(SCHEMA_PATH, payload)
    _require(
        payload["canonical_order_flow_input_gate_status"] == "SATISFIED_FOR_INPUT_IDENTITY_ONLY",
        "canonical order-flow input gate must be satisfied only for input identity",
    )
    _require(
        payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION",
        "order-flow source decision must remain open",
    )
    _require(
        payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_NOT_ROW_MASKED",
        "order-flow era map must remain unsatisfied until row masks are implemented",
    )
    _require(
        payload["archived_cvd_policy"] == "FORBIDDEN_RECOMPUTE_PIT_FOLD_LOCAL_IF_USED",
        "archived CVD must stay forbidden",
    )
    _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    for forbidden in (str(MANIFEST_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "canonical order-flow manifest output must not include local paths")
    print("Phase 38 artifacts validated")


if __name__ == "__main__":
    main()

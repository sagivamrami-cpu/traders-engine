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

SCHEMA_PATH = ROOT / "schemas/gc_canonical_ohlcv_input_manifest.schema.json"
MANIFEST_PATH = ROOT / "configs/data/gc-canonical-ohlcv-input-manifest.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase36.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_canonical_ohlcv_input_manifest.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_canonical_ohlcv_input_manifest.py"),
            "--manifest",
            str(MANIFEST_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    validate_json_payload(SCHEMA_PATH, payload)
    _require(
        payload["canonical_ohlcv_input_gate_status"] == "SATISFIED_FOR_OHLCV_ONLY",
        "canonical OHLCV input gate must be satisfied only for OHLCV",
    )
    _require(
        payload["dataset_identity_gate_status"] == "UNSATISFIED_PARTIAL_INPUT_IDENTITY_ONLY",
        "dataset identity must remain unsatisfied",
    )
    _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    for forbidden in (str(MANIFEST_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "canonical OHLCV manifest output must not include local paths")
    print("Phase 37 artifacts validated")


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

DIAGNOSTICS_PATH = ROOT / "configs/models/gc-model-diagnostics-report.json"
BASELINE_PATH = ROOT / "configs/models/gc-majority-baseline-training-run.json"
FIRST_MODEL_PATH = ROOT / "configs/models/gc-first-real-model-run.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _contains_local_path(value: object) -> bool:
    if isinstance(value, dict):
        return any(_contains_local_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_local_path(item) for item in value)
    if isinstance(value, str):
        return bool(re.search(r"\b[A-Za-z]:\\", value) or re.search(r"/(Users|home|mnt|tmp)/", value))
    return False


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase48.py")])
    validate_json_payload(ROOT / "schemas/gc_model_diagnostics_report.schema.json", load_json(DIAGNOSTICS_PATH))

    diagnostics = load_json(DIAGNOSTICS_PATH)
    baseline = load_json(BASELINE_PATH)
    first_model = load_json(FIRST_MODEL_PATH)

    _require(diagnostics["dataset_id"] == first_model["dataset_id"], "diagnostics dataset_id must match first model")
    _require(diagnostics["baseline_run_id"] == baseline["run_id"], "diagnostics baseline run id mismatch")
    _require(diagnostics["first_model_run_id"] == first_model["run_id"], "diagnostics first model run id mismatch")
    _require(diagnostics["promotion_allowed"] is False, "diagnostics must not allow model promotion")
    _require(diagnostics["status"] == "FEATURE_DIAGNOSTICS_REQUIRED", "Phase 49 must require feature diagnostics")
    _require("NEGATIVE_TEST_EXPECTED_R" in diagnostics["blocked_reasons"], "negative TEST expected R must block")
    _require(
        "TEST_ACCURACY_NOT_ABOVE_BASELINE" in diagnostics["blocked_reasons"],
        "not beating baseline on TEST accuracy must block",
    )
    _require(
        diagnostics["recommended_next_phase"] == "PHASE_50_FEATURE_DIAGNOSTICS_AND_EXPERIMENT_DESIGN",
        "diagnostics must route to feature diagnostics and experiment design",
    )
    _require(not _contains_local_path(diagnostics), "diagnostics report must not contain local machine paths")

    print("Phase 49 artifacts validated")


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

REPORT_PATH = ROOT / "configs/models/gc-normalized-model-stability-report.json"
MODEL_RUN_PATH = ROOT / "configs/models/gc-normalized-feature-model-run.json"
FEATURE_CANDIDATES_PATH = ROOT / "configs/models/gc-normalized-feature-candidates-report.json"


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
    _run([sys.executable, str(ROOT / "tools/validate_phase52.py")])
    validate_json_payload(ROOT / "schemas/gc_normalized_model_stability_report.schema.json", load_json(REPORT_PATH))

    report = load_json(REPORT_PATH)
    model_run = load_json(MODEL_RUN_PATH)
    feature_candidates = load_json(FEATURE_CANDIDATES_PATH)

    _require(report["status"] == "STABILITY_REVIEW_REQUIRED", "Phase 53 must require stability review")
    _require(report["dataset_id"] == model_run["dataset_id"], "stability report dataset_id mismatch")
    _require(report["variant"] == "order_flow", "Phase 53 must target order_flow")
    _require(report["source_model_run_id"] == model_run["run_id"], "Phase 52 model run id mismatch")
    _require(
        report["source_feature_candidates_report_id"] == feature_candidates["report_id"],
        "Phase 51 feature candidates id mismatch",
    )
    _require(report["evaluation_scope"] == "TEST_ONLY", "stability review must evaluate TEST only")
    _require(
        report["preprocessing_reconstruction_scope"] == "TRAIN_ONLY",
        "preprocessing must be reconstructed from TRAIN only",
    )
    _require(report["promotion_allowed"] is False, "stability report must not allow promotion")
    _require(report["monthly_test_segments"], "monthly TEST segments missing")
    _require(set(report["direction_test_segments"]) == {"LONG", "SHORT"}, "direction segments missing")
    _require(set(report["volatility_test_segments"]) == {"LOW", "MID", "HIGH"}, "volatility segments missing")
    _require(len(report["threshold_stability"]) == 3, "threshold stability must include three checks")
    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in report["blocked_actions"], f"blocked action missing: {action}")
    _require(report["recommended_next_phase"] == "PHASE_54_WALK_FORWARD_RETRAINING_EXPERIMENTS", "next phase changed")
    _require(not _contains_local_path(report), "stability report must not contain local machine paths")

    print("Phase 53 artifacts validated")


if __name__ == "__main__":
    main()

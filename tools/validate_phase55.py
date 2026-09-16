from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

RUN_PATH = ROOT / "configs/models/gc-bounded-walk-forward-retraining-run.json"
EXPERIMENT_REPORT_PATH = ROOT / "configs/models/gc-walk-forward-experiments-report.json"
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
    _run([sys.executable, str(ROOT / "tools/validate_phase54.py")])
    validate_json_payload(ROOT / "schemas/gc_bounded_walk_forward_retraining_run.schema.json", load_json(RUN_PATH))

    run = load_json(RUN_PATH)
    experiment_report = load_json(EXPERIMENT_REPORT_PATH)
    feature_candidates = load_json(FEATURE_CANDIDATES_PATH)

    _require(run["status"] == "WALK_FORWARD_RETRAINING_EXECUTED", "Phase 55 must execute at least one window")
    _require(run["dataset_id"] == experiment_report["dataset_id"], "walk-forward run dataset_id mismatch")
    _require(run["variant"] == "order_flow", "Phase 55 must target order_flow")
    _require(run["source_experiment_report_id"] == experiment_report["report_id"], "experiment report id mismatch")
    _require(
        run["source_feature_candidates_report_id"] == feature_candidates["report_id"],
        "feature candidates report id mismatch",
    )
    _require(run["feature_names"] == feature_candidates["next_model_feature_set"], "feature names changed")
    _require(run["research_execution_allowed"] is False, "research execution must close after run artifact")
    _require(run["model_promotion_allowed"] is False, "model promotion must remain blocked")
    experiment_ids = {item["experiment_id"] for item in run["experiment_results"]}
    _require(
        "LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING" in experiment_ids,
        "primary long mid/high result missing",
    )
    _require("ALL_CANDIDATES_WALK_FORWARD_COMPARATOR" in experiment_ids, "comparator result missing")
    comparator = next(item for item in run["experiment_results"] if item["experiment_id"] == "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR")
    _require(comparator["valid_window_count"] > 0, "comparator must have valid windows")
    for result in run["experiment_results"]:
        _require(result["attempted_window_count"] <= 8, f"too many windows: {result['experiment_id']}")
    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in run["blocked_actions"], f"blocked action missing: {action}")
    _require(
        run["recommended_next_phase"] == "PHASE_56_WALK_FORWARD_RESULTS_REVIEW",
        "next phase changed",
    )
    _require(not _contains_local_path(run), "walk-forward run must not contain local machine paths")

    print("Phase 55 artifacts validated")


if __name__ == "__main__":
    main()

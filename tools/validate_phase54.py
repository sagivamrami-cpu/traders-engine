from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

REPORT_PATH = ROOT / "configs/models/gc-walk-forward-experiments-report.json"
STABILITY_REPORT_PATH = ROOT / "configs/models/gc-normalized-model-stability-report.json"


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
    _run([sys.executable, str(ROOT / "tools/validate_phase53.py")])
    validate_json_payload(ROOT / "schemas/gc_walk_forward_experiments_report.schema.json", load_json(REPORT_PATH))

    report = load_json(REPORT_PATH)
    stability = load_json(STABILITY_REPORT_PATH)

    _require(report["status"] == "WALK_FORWARD_EXPERIMENTS_READY", "Phase 54 status changed")
    _require(report["dataset_id"] == stability["dataset_id"], "walk-forward report dataset_id mismatch")
    _require(report["variant"] == "order_flow", "Phase 54 must target order_flow")
    _require(report["source_stability_report_id"] == stability["report_id"], "stability report id mismatch")
    _require(report["source_model_run_id"] == stability["source_model_run_id"], "source model run id mismatch")
    _require(
        report["source_feature_candidates_report_id"] == stability["source_feature_candidates_report_id"],
        "source feature candidates id mismatch",
    )
    _require(report["research_execution_allowed"] is True, "research execution should be allowed")
    _require(report["model_promotion_allowed"] is False, "model promotion must remain blocked")
    _require(report["experiment_budget"]["max_windows"] <= 8, "Phase 54 must stay compute bounded")
    _require(report["experiment_budget"]["epochs_per_window"] <= 80, "Phase 54 epoch budget changed")
    experiment_ids = {item["experiment_id"] for item in report["recommended_experiments"]}
    _require(
        "LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING" in experiment_ids,
        "primary long mid/high experiment missing",
    )
    _require("ALL_CANDIDATES_WALK_FORWARD_COMPARATOR" in experiment_ids, "comparator experiment missing")
    _require("SHORT_ONLY_DIAGNOSTIC_WALK_FORWARD_RETRAINING" in experiment_ids, "short diagnostic missing")
    for experiment in report["recommended_experiments"]:
        _require(experiment["promotion_use"] == "FORBIDDEN", f"promotion use changed: {experiment['experiment_id']}")
    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in report["blocked_actions"], f"blocked action missing: {action}")
    _require(
        report["recommended_next_phase"] == "PHASE_55_EXECUTE_BOUNDED_WALK_FORWARD_RETRAINING",
        "next phase changed",
    )
    _require(not _contains_local_path(report), "walk-forward report must not contain local machine paths")

    print("Phase 54 artifacts validated")


if __name__ == "__main__":
    main()

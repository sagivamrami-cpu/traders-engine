from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

REPORT_PATH = ROOT / "configs/models/gc-feature-diagnostics-report.json"
BUILD_MANIFEST_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
MODEL_DIAGNOSTICS_PATH = ROOT / "configs/models/gc-model-diagnostics-report.json"


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
    _run([sys.executable, str(ROOT / "tools/validate_phase49.py")])
    validate_json_payload(ROOT / "schemas/gc_feature_diagnostics_report.schema.json", load_json(REPORT_PATH))

    report = load_json(REPORT_PATH)
    manifest = load_json(BUILD_MANIFEST_PATH)
    diagnostics = load_json(MODEL_DIAGNOSTICS_PATH)

    _require(report["status"] == "EXPERIMENT_DESIGN_REQUIRED", "Phase 50 must route to experiment design")
    _require(report["dataset_id"] == manifest["dataset_id"], "feature diagnostics dataset_id mismatch")
    _require(report["variant"] == "order_flow", "Phase 50 must diagnose the order_flow variant")
    _require(report["diagnostic_focus"] == "FEATURE_AND_REGIME_STABILITY", "diagnostic focus changed")
    _require(report["source_model_diagnostics_report_id"] == diagnostics["report_id"], "Phase 49 report id mismatch")
    _require(report["promotion_allowed"] is False, "feature diagnostics must not allow promotion")
    _require(report["included_rows_by_split"] == manifest["summary"]["variants"]["order_flow"]["included_rows_by_split"], "split counts changed")
    _require(report["top_drift_features"], "top drift features must be present")
    _require(report["regime_summaries"], "regime summaries must be present")
    for regime in ("direction=LONG", "direction=SHORT"):
        _require(regime in report["regime_summaries"], f"regime missing: {regime}")
    for experiment in ("REGIME_FILTER_RESEARCH", "THRESHOLD_STABILITY_REVIEW", "FAILED_TRADE_CLUSTER_REVIEW"):
        _require(experiment in report["recommended_experiments"], f"experiment missing: {experiment}")
    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in report["blocked_actions"], f"blocked action missing: {action}")
    _require(not _contains_local_path(report), "feature diagnostics report must not contain local machine paths")

    print("Phase 50 artifacts validated")


if __name__ == "__main__":
    main()

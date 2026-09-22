from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

REPORT_PATH = ROOT / "configs/models/gc-normalized-feature-candidates-report.json"
FEATURE_DIAGNOSTICS_PATH = ROOT / "configs/models/gc-feature-diagnostics-report.json"
REQUIRED_NORMALIZED_FEATURES = {
    "atr_14_over_close",
    "of_delta_over_of_volume",
    "of_delta_sum_14_over_of_volume_sum_14",
    "of_trades_per_minute",
    "of_volume_per_trade",
    "of_volume_vs_14bar_avg",
    "of_trades_vs_14bar_avg",
}
FORBIDDEN_FEATURES = {
    "close",
    "atr_14",
    "outcome_class",
    "net_return_r",
    "time_to_outcome_bars",
    "entry_price",
    "target_price",
    "stop_price",
    "risk_r",
}


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
    _run([sys.executable, str(ROOT / "tools/validate_phase50.py")])
    validate_json_payload(ROOT / "schemas/gc_normalized_feature_candidates_report.schema.json", load_json(REPORT_PATH))

    report = load_json(REPORT_PATH)
    feature_diagnostics = load_json(FEATURE_DIAGNOSTICS_PATH)
    feature_set = set(report["next_model_feature_set"])

    _require(report["status"] == "NORMALIZED_FEATURE_CANDIDATES_READY", "Phase 51 must produce candidate features")
    _require(report["dataset_id"] == feature_diagnostics["dataset_id"], "normalized report dataset_id mismatch")
    _require(report["variant"] == "order_flow", "Phase 51 must target order_flow")
    _require(
        report["source_feature_diagnostics_report_id"] == feature_diagnostics["report_id"],
        "Phase 50 report id mismatch",
    )
    _require(report["source_feature_diagnostics_status"] == "EXPERIMENT_DESIGN_REQUIRED", "Phase 50 status mismatch")
    _require(report["included_rows_by_split"] == feature_diagnostics["included_rows_by_split"], "split counts changed")
    _require(report["research_training_allowed"] is True, "next research training should be allowed")
    _require(report["model_promotion_allowed"] is False, "model promotion must remain blocked")
    _require(not (feature_set & FORBIDDEN_FEATURES), f"forbidden feature inputs present: {sorted(feature_set & FORBIDDEN_FEATURES)}")
    _require(REQUIRED_NORMALIZED_FEATURES.issubset(feature_set), "required normalized features missing")
    _require(
        {"feature": "close", "reason": "RAW_PRICE_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"} in report["excluded_raw_features"],
        "raw close exclusion missing",
    )
    _require(
        {"feature": "atr_14", "reason": "RAW_ATR_FEATURE_EXCLUDED_FOR_REGIME_DRIFT"} in report["excluded_raw_features"],
        "raw atr_14 exclusion missing",
    )
    for control in (
        "TRAIN_ONLY_IMPUTATION_AND_STANDARDIZATION",
        "VALIDATION_ONLY_THRESHOLD_SELECTION",
        "TEST_ONLY_FINAL_EVALUATION",
        "NO_LABEL_OR_OUTCOME_FEATURE_INPUTS",
    ):
        _require(control in report["required_training_controls"], f"training control missing: {control}")
    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in report["blocked_actions"], f"blocked action missing: {action}")
    _require(report["recommended_next_phase"] == "PHASE_52_NORMALIZED_FEATURE_MODEL_RETRAINING", "next phase changed")
    _require(not _contains_local_path(report), "normalized feature candidates report must not contain local machine paths")

    print("Phase 51 artifacts validated")


if __name__ == "__main__":
    main()

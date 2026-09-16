from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

RUN_PATH = ROOT / "configs/models/gc-normalized-feature-model-run.json"
FEATURE_CANDIDATES_PATH = ROOT / "configs/models/gc-normalized-feature-candidates-report.json"
PREVIOUS_MODEL_PATH = ROOT / "configs/models/gc-first-real-model-run.json"
BASELINE_PATH = ROOT / "configs/models/gc-majority-baseline-training-run.json"
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
    _run([sys.executable, str(ROOT / "tools/validate_phase51.py")])
    validate_json_payload(ROOT / "schemas/gc_normalized_feature_model_run.schema.json", load_json(RUN_PATH))

    run = load_json(RUN_PATH)
    feature_candidates = load_json(FEATURE_CANDIDATES_PATH)
    previous_model = load_json(PREVIOUS_MODEL_PATH)
    baseline = load_json(BASELINE_PATH)
    feature_names = set(run["feature_names"])

    _require(run["status"] == "TRAINED", "Phase 52 must produce a trained research run")
    _require(run["dataset_id"] == feature_candidates["dataset_id"], "normalized model dataset_id mismatch")
    _require(run["model_type"] == "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH", "wrong model type")
    _require(run["promotion_allowed"] is False, "normalized model must not allow promotion")
    _require(run["fit_scope"] == "TRAIN_ONLY", "fit scope changed")
    _require(run["selection_scope"] == "VALIDATION_ONLY", "selection scope changed")
    _require(run["final_evaluation_scope"] == "TEST_ONLY", "final evaluation scope changed")
    _require(
        run["source_feature_candidates_report_id"] == feature_candidates["report_id"],
        "Phase 51 report id mismatch",
    )
    _require(run["source_previous_model_run_id"] == previous_model["run_id"], "previous model run id mismatch")
    _require(run["source_baseline_run_id"] == baseline["run_id"], "baseline run id mismatch")
    _require(not (feature_names & FORBIDDEN_FEATURES), f"forbidden feature inputs present: {sorted(feature_names & FORBIDDEN_FEATURES)}")
    _require(REQUIRED_NORMALIZED_FEATURES.issubset(feature_names), "required normalized features missing")
    _require("validation_expected_r_per_candidate" in run["metrics"], "validation expected-R metric missing")
    _require("test_expected_r_per_candidate" in run["metrics"], "test expected-R metric missing")
    _require("test_accuracy_delta_vs_previous_model" in run["comparison_metrics"], "previous model comparison missing")
    _require("test_accuracy_delta_vs_baseline" in run["comparison_metrics"], "baseline comparison missing")
    _require(not _contains_local_path(run), "normalized feature model run must not contain local machine paths")

    print("Phase 52 artifacts validated")


if __name__ == "__main__":
    main()

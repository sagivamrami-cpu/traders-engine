from __future__ import annotations

import subprocess
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.models.first_real_gc_model import APPROVED_FEATURE_NAMES

BUILD_MANIFEST_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
RUN_PATH = ROOT / "configs/models/gc-first-real-model-run.json"
SANITIZED_TEXT_ARTIFACTS = (
    RUN_PATH,
    ROOT / "docs/implementation-reports/phase-48-first-real-gc-model.md",
    ROOT / "agent-exchange/status/2026-09-07T135009Z-codex-phase-48-first-real-gc-model-result.md",
    ROOT / "agent-exchange/status/2026-09-07T135500Z-codex-phase-48-review-takeover.md",
    ROOT / "agent-exchange/inbox/claude-code/2026-09-07T135009Z-claude-code-review-phase-48-first-real-gc-model.md",
)


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


def _text_contains_local_path(path: Path) -> bool:
    return _contains_local_path(path.read_text(encoding="utf-8"))


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase47.py")])
    validate_json_payload(ROOT / "schemas/gc_first_real_model_run.schema.json", load_json(RUN_PATH))

    manifest = load_json(BUILD_MANIFEST_PATH)
    run = load_json(RUN_PATH)
    order_flow = manifest["summary"]["variants"]["order_flow"]

    _require(run["status"] == "TRAINED", "first real GC model run must be trained")
    _require(
        run["model_type"] == "REGULARIZED_LOGISTIC_RESEARCH_BASELINE",
        "Phase 48 model must be the first real logistic research baseline",
    )
    _require(run["model_type"] != "MAJORITY_CLASS_BASELINE", "Phase 48 must not validate the majority baseline")
    _require(run["dataset_id"] == manifest["dataset_id"], "model run dataset_id must match Phase 46 manifest")
    _require(run["dataset_version"] == manifest["builder_version"], "model run dataset_version must match builder")
    _require(run["feature_schema_version"] == manifest["feature_schema_version"], "feature schema changed")
    _require(run["label_version"] == manifest["label_version"], "label version changed")
    _require(run["split_summary"] == order_flow["included_rows_by_split"], "model split summary must match order-flow rows")
    _require(run["class_distribution"] == order_flow["included_outcome_class_counts"], "class distribution changed")
    _require(run["fit_scope"] == "TRAIN_ONLY", "model transforms must be fit only on TRAIN")
    _require(run["selection_scope"] == "VALIDATION_ONLY", "threshold selection must use VALIDATION only")
    _require(run["final_evaluation_scope"] == "TEST_ONLY", "final metrics must be TEST only")
    _require(run["promotion_allowed"] is False, "first real model promotion must remain blocked")
    _require(run["blocked_reasons"] == [], "trained first real model must not carry training blockers")
    _require(run["selected_threshold"] is not None, "trained model must record selected threshold")
    _require(run["feature_names"], "trained model must record feature names")
    allowed_run_features = {*APPROVED_FEATURE_NAMES, "direction_is_long", "direction_is_short"}
    unexpected_features = sorted(set(run["feature_names"]) - allowed_run_features)
    _require(not unexpected_features, f"run feature names include unapproved features: {unexpected_features}")
    for required_feature in ("ret_1", "ret_4", "ret_8", "ret_14", "of_delta", "of_volume", "direction_is_long"):
        _require(required_feature in run["feature_names"], f"feature missing: {required_feature}")
    for required_metric in (
        "validation_accuracy",
        "test_accuracy",
        "validation_expected_r_per_candidate",
        "test_expected_r_per_candidate",
        "validation_selected_trade_rate",
        "test_selected_trade_rate",
    ):
        _require(required_metric in run["metrics"], f"metric missing: {required_metric}")
    _require(not _contains_local_path(run), "first real model run must not contain local machine paths")
    for artifact in SANITIZED_TEXT_ARTIFACTS:
        _require(artifact.is_file(), f"Phase 48 text artifact is missing: {artifact.name}")
        _require(not _text_contains_local_path(artifact), f"Phase 48 artifact contains a local machine path: {artifact.name}")

    print("Phase 48 artifacts validated")


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

REVIEW_PATH = ROOT / "configs/models/gc-tree-translation-gap-review.json"
WALK_FORWARD_RUN_PATH = ROOT / "configs/models/gc-bounded-walk-forward-retraining-run.json"


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
    _run([sys.executable, str(ROOT / "tools/validate_phase55.py")])
    validate_json_payload(ROOT / "schemas/gc_tree_translation_gap_review.schema.json", load_json(REVIEW_PATH))

    review = load_json(REVIEW_PATH)
    run = load_json(WALK_FORWARD_RUN_PATH)

    _require(review["status"] == "TREE_TRANSLATION_REDESIGN_REQUIRED", "Phase 56 status changed")
    _require(review["dataset_id"] == run["dataset_id"], "tree gap review dataset_id mismatch")
    _require(review["variant"] == "order_flow", "Phase 56 must target order_flow")
    _require(review["source_walk_forward_run_id"] == run["run_id"], "walk-forward run id mismatch")
    _require(
        review["source_experiment_report_id"] == run["source_experiment_report_id"],
        "experiment report id mismatch",
    )
    _require(review["additional_model_training_allowed"] is False, "additional flat model training must be blocked")
    _require(review["model_promotion_allowed"] is False, "model promotion must remain blocked")
    for gap in (
        "FLAT_MODEL_INSTEAD_OF_TREE_GATE_POLICY",
        "CANDIDATE_SELECTION_TOO_BROAD",
        "LABEL_TOO_NARROW_FOR_MANUAL_TRADING_PROCESS",
        "TREE_STAGE_COVERAGE_INCOMPLETE",
        "RULE_ONLY_TREE_BASELINE_MISSING",
    ):
        _require(gap in review["gap_codes"], f"gap missing: {gap}")
    for stage in ("DATA", "SESSION", "LOCATION", "CYCLE", "CONTEXT", "VECTOR", "TRIGGER", "INVALIDATION"):
        _require(stage in review["tree_stage_coverage"], f"stage missing: {stage}")
    _require(
        review["tree_stage_coverage"]["VECTOR"]["current_coverage"] == "MISSING_AS_TYPED_TREE_STAGE",
        "vector must still be missing as typed tree stage",
    )
    _require(review["required_next_artifacts"][0] == "rule_only_tree_baseline", "rule-only tree baseline must be first")
    for action in ("TRAIN_ADDITIONAL_FLAT_MODEL", "MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in review["blocked_actions"], f"blocked action missing: {action}")
    _require(
        review["recommended_next_phase"] == "PHASE_57_TREE_GATE_BASELINE_AND_CANDIDATE_AUDIT",
        "next phase changed",
    )
    _require(not _contains_local_path(review), "tree gap review must not contain local machine paths")

    print("Phase 56 artifacts validated")


if __name__ == "__main__":
    main()

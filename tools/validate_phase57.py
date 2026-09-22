from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

AUDIT_PATH = ROOT / "configs/models/gc-tree-gate-baseline-audit.json"
TREE_GAP_REVIEW_PATH = ROOT / "configs/models/gc-tree-translation-gap-review.json"


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
    _run([sys.executable, str(ROOT / "tools/validate_phase56.py")])
    validate_json_payload(ROOT / "schemas/gc_tree_gate_baseline_audit.schema.json", load_json(AUDIT_PATH))

    audit = load_json(AUDIT_PATH)
    review = load_json(TREE_GAP_REVIEW_PATH)

    _require(audit["status"] == "TREE_GATE_BASELINE_AUDIT_READY", "Phase 57 status changed")
    _require(audit["dataset_id"] == review["dataset_id"], "tree gate audit dataset_id mismatch")
    _require(audit["variant"] == "order_flow", "Phase 57 must target order_flow")
    _require(audit["source_tree_gap_review_id"] == review["review_id"], "tree gap review id mismatch")
    _require(len(audit["gate_catalog"]) == 14, "gate catalog must include 14 TR runtime stages")
    for stage in ("DATA", "SESSION", "LOCATION", "CYCLE", "CONTEXT", "VECTOR", "TRIGGER", "INVALIDATION"):
        _require(stage in audit["stage_summary"], f"stage summary missing: {stage}")
    _require(
        audit["aggregate_counts"]["final_actions"]["LONG"] == 0
        and audit["aggregate_counts"]["final_actions"]["SHORT"] == 0,
        "conservative baseline must not emit directional trades",
    )
    _require(audit["aggregate_counts"]["final_actions"]["WAIT"] > 0, "audit must expose WAIT candidates")
    _require(audit["stage_summary"]["VECTOR"]["UNKNOWN"] > 0, "missing VECTOR gate must be visible")
    _require(audit["additional_model_training_allowed"] is False, "additional flat model training must stay blocked")
    _require(audit["model_promotion_allowed"] is False, "model promotion must remain blocked")
    for action in ("TRAIN_ADDITIONAL_FLAT_MODEL", "MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in audit["blocked_actions"], f"blocked action missing: {action}")
    _require(
        audit["recommended_next_phase"] == "PHASE_58_TYPED_TREE_GATE_IMPLEMENTATION",
        "next phase changed",
    )
    _require(not _contains_local_path(audit), "tree gate audit must not contain local machine paths")

    print("Phase 57 artifacts validated")


if __name__ == "__main__":
    main()

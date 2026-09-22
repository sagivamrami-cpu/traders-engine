from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json

SCHEMA_PATH = ROOT / "schemas/gc_label_split_policy.schema.json"
POLICY_PATH = ROOT / "configs/research/gc-label-split-policy.yaml"

# Retargeted after Phase 41 (D7/D8 approved, ROLL/LABEL/SPLIT gates closed)
# and Phase 42 (SESSION_CALENDAR closed), mirroring validate_phase24/25/28.
# The label/split policy is now an approved contract; dataset construction,
# label building, split building, and training must still remain blocked.


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase28.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_label_split_policy.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_label_split_policy.py"),
            "--policy",
            str(POLICY_PATH),
        ]
    )
    payload = json.loads(result.stdout)
    _require(
        payload["status"] == "APPROVED_LABEL_SPLIT_CONTRACTS_DATASET_CONSTRUCTION_AUTHORIZED",
        "policy must reflect approved label/split contracts with construction authorized",
    )
    _require(
        payload["candidate_timeframe"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1",
        "label/split policy must reflect D1-approved v1 baseline timeframe",
    )
    _require(payload["dataset_construction_allowed"] is True, "identified dataset construction must be authorized")
    _require(payload["label_building_allowed"] is True, "label building for the identified build must be allowed")
    _require(payload["split_building_allowed"] is True, "split building for the identified build must be allowed")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    _require(
        payload["label_contract_policy"]["d7_decision_status"] == "APPROVED_DECISION_RECORDED",
        "D7 must be backed by an approved human decision record",
    )
    _require(
        payload["label_contract_policy"]["decision_ref"].endswith("human-d7-final-label-contract.md"),
        "D7 decision ref must point at the D7-final record",
    )
    _require(
        payload["label_contract_policy"]["primary_label_family"] == "OUTCOME_CONTRACT_LABEL",
        "primary label must be outcome-contract based",
    )
    _require(
        payload["label_contract_policy"]["hhll_role"] == "AUXILIARY_DIRECTION_LABEL_ONLY_NOT_TRAINING_TARGET",
        "HHLL must not be a training target",
    )
    _require(
        payload["label_contract_policy"]["hhll_auxiliary_training_status"]
        == "BLOCKED_PENDING_SEPARATE_PIT_LABEL_STUDY",
        "HHLL auxiliary training must remain blocked",
    )
    _require(
        payload["label_contract_policy"]["ambiguous_label_quality_requirement"]
        == "LABEL_QUALITY_EXCLUDED_FROM_TRAINING_REQUIRED",
        "ambiguous labels must require excluded-from-training quality",
    )
    _require(
        payload["label_contract_policy"]["binary_projection_status"]
        == "AMBIGUOUS_ROWS_EXCLUDED_BEFORE_BINARY_PROJECTION",
        "binary projection must exclude ambiguous rows first",
    )
    _require(
        payload["label_contract_policy"]["same_bar_target_and_stop_policy"] == "AMBIGUOUS_EXCLUDED_FROM_TRAINING",
        "same-bar target/stop ambiguity must be excluded",
    )
    _require(
        payload["label_contract_policy"]["fill_truth_status"]
        == "ZERO_COST_RESEARCH_SIMULATOR_ONLY_NOT_EXECUTION_TRUTH",
        "fill truth must remain research-simulator only",
    )
    _require(
        payload["split_and_embargo_policy"]["d8_decision_status"] == "APPROVED_DECISION_RECORDED",
        "D8 must be backed by an approved human decision record",
    )
    _require(
        payload["split_and_embargo_policy"]["decision_ref"].endswith("human-d8-final-split-embargo-policy.md"),
        "D8 decision ref must point at the D8-final record",
    )
    _require(
        payload["split_and_embargo_policy"]["split_method"] == "CHRONOLOGICAL_WALK_FORWARD_ONLY",
        "split policy must be chronological walk-forward",
    )
    _require(
        payload["split_and_embargo_policy"]["random_split_allowed"] is False,
        "random time-series split must remain blocked",
    )
    _require(payload["split_and_embargo_policy"]["embargo_required"] is True, "embargo must be required")
    _require(
        payload["split_and_embargo_policy"]["embargo_size_status"] == "SPECIFIED_8_BARS_MATCHES_MAX_LABEL_HORIZON",
        "embargo size must match the max label horizon",
    )
    _require(payload["split_and_embargo_policy"]["embargo_bars"] == 8, "embargo must be 8 bars")
    _require(
        payload["split_and_embargo_policy"]["purge_rule_status"] == "PURGE_OVERLAPPING_8_BAR_LABEL_HORIZON",
        "purge rule must cover the 8-bar label horizon",
    )
    _require(
        payload["split_and_embargo_policy"]["fold_fit_scope"]
        == "FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW",
        "fit scope must be train-window only",
    )
    _require(
        payload["split_and_embargo_policy"]["damaged_2017_mask_policy"]
        == "APPLY_IDENTICALLY_TO_ALL_DATASET_AND_MODEL_VARIANTS",
        "2017 damaged window mask must apply to every variant",
    )
    _require(
        payload["split_and_embargo_policy"]["row_level_2017_mask_status"]
        == "SATISFIED_SHARED_ORDER_FLOW_MASK_FUNCTION",
        "row-level 2017 mask must be the shared order-flow mask function",
    )
    required_gates = set(payload["required_remaining_gates"])
    _require(not required_gates, f"no gate may remain on the label/split policy: {sorted(required_gates)}")
    for closed_gate in (
        "MISSING_BAR_POLICY",
        "DATASET_IDENTITY",
        "DATASET_CONSTRUCTION_AUTHORIZATION",
        "BAR_BOUNDARY",
        "TIMESTAMP_ROLE",
        "AVAILABLE_AT_POLICY",
        "SESSION_CALENDAR",
        "ROLL_POLICY",
        "CONTRACT_IDENTITY",
        "GRAPH_TRADE_CONTRACT",
        "COST_FILL_POLICY",
        "LABEL_CONTRACT",
        "SPLIT_AND_EMBARGO_POLICY",
        "ROW_LEVEL_2017_MASK",
        "ORDER_FLOW_SOURCE_DECISION",
    ):
        _require(closed_gate not in required_gates, f"closed gate still present: {closed_gate}")
    for action in ("BUILD_REAL_DATASET", "BUILD_REAL_LABELS", "BUILD_REAL_SPLITS"):
        _require(action not in payload["blocked_actions"], f"identified build step must not be blocked: {action}")
    for action in (
        "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
        "INGEST_HHLL_DERIVED_LABELS",
        "JOIN_HHLL_FILES_TO_TRAINING_ROWS",
        "USE_HHLL_AS_AUXILIARY_TRAINING_TARGET",
        "ADAPT_FIXTURE_TRADE_CONTRACT_TO_REAL_GC",
        "RANDOM_SPLIT_TIME_SERIES_ROWS",
        "BUILD_UNEMBARGOED_SPLITS",
        "USE_FIXTURE_WALK_FORWARD_POLICY",
        "USE_AMBIGUOUS_LABELS_FOR_TRAINING",
        "USE_BINARY_PROJECTION_WITH_AMBIGUOUS_AS_NEGATIVE",
        "TRAIN_PRODUCTION_MODEL",
        "MODEL_PROMOTION",
        "LIVE_TRADING",
        "BROKER_EXECUTION",
        "CAPITAL_ALLOCATION",
    ):
        _require(action in payload["blocked_actions"], f"blocked action missing: {action}")
    _require(payload["blocked_reasons"] == [], "no blocked reason may remain on the label/split policy")
    for stale_reason in (
        "UPSTREAM_DATASET_GATES_UNSATISFIED",
        "LABEL_CONTRACT_GATE_UNSATISFIED",
        "SPLIT_AND_EMBARGO_POLICY_GATE_UNSATISFIED",
        "D7_DECISION_RECORD_MISSING",
        "D8_DECISION_RECORD_MISSING",
        "TARGET_STOP_THRESHOLDS_UNSPECIFIED",
        "MAX_LABEL_HORIZON_UNSPECIFIED",
        "EMBARGO_SIZE_UNSPECIFIED",
        "ROW_LEVEL_2017_MASK_NOT_IMPLEMENTED",
        "CONTRACT_IDENTITY_AND_FILL_TRUTH_UNSATISFIED",
    ):
        _require(stale_reason not in payload["blocked_reasons"], f"resolved blocker reappeared: {stale_reason}")
    for forbidden in (str(POLICY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "label/split policy output must not include local paths")
    print("Phase 29 artifacts validated")


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_tree_translation_gap_review.schema.json"
REVIEW_VERSION = "gc-tree-translation-gap-review-0.1.0"
MODE = "GC_TREE_TRANSLATION_GAP_REVIEW"
BLOCKED_ACTIONS = [
    "TRAIN_ADDITIONAL_FLAT_MODEL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]

TREE_STAGES = [
    "DATA",
    "POSITION",
    "SESSION",
    "LOCATION",
    "CYCLE",
    "CONTEXT",
    "PATTERN",
    "VECTOR",
    "TRAP",
    "RETEST",
    "TARGET_RISK",
    "TRIGGER",
    "SCALE_IN",
    "INVALIDATION",
]
PARTIAL_FEATURE_STAGES = {"DATA", "SESSION", "CONTEXT", "TARGET_RISK"}


@dataclass(frozen=True)
class GcTreeTranslationGapReview:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _review_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "review_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _comparator(run: dict[str, Any]) -> dict[str, Any]:
    return next(
        item
        for item in run["experiment_results"]
        if item["experiment_id"] == "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR"
    )


def _filtered_without_valid_windows(run: dict[str, Any]) -> list[str]:
    return [
        item["experiment_id"]
        for item in run["experiment_results"]
        if item["experiment_id"] != "ALL_CANDIDATES_WALK_FORWARD_COMPARATOR"
        and int(item.get("valid_window_count", 0)) == 0
    ]


def _walk_forward_findings(run: dict[str, Any]) -> dict[str, Any]:
    comparator = _comparator(run)
    decision = run["decision_summary"]
    return {
        "best_primary_experiment_id": decision.get("best_primary_experiment_id"),
        "best_primary_median_test_expected_r_per_candidate": decision.get(
            "best_primary_median_test_expected_r_per_candidate"
        ),
        "comparator_median_test_expected_r_per_candidate": decision.get(
            "comparator_median_test_expected_r_per_candidate"
        ),
        "comparator_valid_windows": int(comparator["valid_window_count"]),
        "comparator_positive_windows": int(comparator["positive_test_window_count"]),
        "filtered_experiments_without_valid_windows": _filtered_without_valid_windows(run),
        "primary_read": (
            "The all-candidate walk-forward comparator is negative, while filtered variants are mostly underpowered. "
            "The next failure to solve is tree translation, not another flat retraining pass."
        ),
    }


def _tree_stage_coverage() -> dict[str, dict[str, Any]]:
    coverage = {}
    for index, stage in enumerate(TREE_STAGES, start=1):
        partial = stage in PARTIAL_FEATURE_STAGES
        coverage[stage] = {
            "stage_order": index,
            "current_coverage": "PARTIAL_AS_FLAT_FEATURES" if partial else "MISSING_AS_TYPED_TREE_STAGE",
            "required_change": (
                "convert existing scalar inputs into a typed gate/stage output with pass/block/reason logging"
                if partial
                else "implement this tree stage as an explicit typed gate before using it as a model feature"
            ),
        }
    return coverage


def build_gc_tree_translation_gap_review(
    walk_forward_run: dict[str, Any],
    *,
    created_at: datetime,
) -> GcTreeTranslationGapReview:
    payload = {
        "review_id": "",
        "review_version": REVIEW_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "TREE_TRANSLATION_REDESIGN_REQUIRED",
        "dataset_id": str(walk_forward_run["dataset_id"]),
        "variant": str(walk_forward_run.get("variant", "order_flow")),
        "source_walk_forward_run_id": str(walk_forward_run["run_id"]),
        "source_experiment_report_id": str(walk_forward_run["source_experiment_report_id"]),
        "source_feature_candidates_report_id": str(walk_forward_run["source_feature_candidates_report_id"]),
        "walk_forward_findings": _walk_forward_findings(walk_forward_run),
        "architecture_contract_refs": [
            "docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md",
            "docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md",
        ],
        "gap_codes": [
            "FLAT_MODEL_INSTEAD_OF_TREE_GATE_POLICY",
            "CANDIDATE_SELECTION_TOO_BROAD",
            "LABEL_TOO_NARROW_FOR_MANUAL_TRADING_PROCESS",
            "TREE_STAGE_COVERAGE_INCOMPLETE",
            "DIRECTION_AND_REGIME_LOGIC_NOT_SEPARATED",
            "MANUAL_SKIP_DECISIONS_NOT_CAPTURED",
            "RULE_ONLY_TREE_BASELINE_MISSING",
        ],
        "tree_stage_coverage": _tree_stage_coverage(),
        "missing_manual_process_elements": [
            {
                "element": "trader skip decision",
                "why_it_matters": "manual traders reject many near-signals that the current candidate factory still trains on",
                "next_artifact": "candidate_rejection_reason_catalog",
            },
            {
                "element": "hierarchical gate path",
                "why_it_matters": "the current model sees flat features and cannot enforce fail-fast tree branches",
                "next_artifact": "typed_tree_gate_trace_schema",
            },
            {
                "element": "setup quality annotation",
                "why_it_matters": "target-before-stop does not distinguish clean setups from noisy or late entries",
                "next_artifact": "manual_replay_annotation_template",
            },
            {
                "element": "direction-specific policy",
                "why_it_matters": "LONG and SHORT behavior diverged materially in stability review and should not share one flat policy",
                "next_artifact": "long_short_separate_gate_baselines",
            },
            {
                "element": "regime-first filtering",
                "why_it_matters": "LOW volatility and all-candidate walk-forward results show that regime context must control candidate admission",
                "next_artifact": "regime_gate_baseline",
            },
        ],
        "required_next_artifacts": [
            "rule_only_tree_baseline",
            "typed_tree_gate_trace_schema",
            "candidate_rejection_reason_catalog",
            "manual_replay_annotation_template",
            "long_short_separate_gate_baselines",
            "regime_gate_baseline",
        ],
        "recommended_redesign": [
            "stop training additional flat models until the tree path is measured as deterministic gates",
            "create a rule-only tree baseline that emits LONG, SHORT, WAIT, or NO_TRADE before model scoring",
            "log pass/block/unknown for every TR runtime stage per candidate",
            "train later models only inside candidates that pass the relevant deterministic tree gates",
            "replace the single target-first label with additional outcome diagnostics such as MFE, MAE, clean follow-through, and failed setup",
            "separate LONG and SHORT experiments after gate coverage is measurable",
        ],
        "additional_model_training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_57_TREE_GATE_BASELINE_AND_CANDIDATE_AUDIT",
    }
    payload["review_id"] = _review_id(payload)
    return GcTreeTranslationGapReview(payload)

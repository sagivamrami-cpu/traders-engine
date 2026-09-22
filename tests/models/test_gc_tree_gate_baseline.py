from dataclasses import replace
from datetime import UTC, datetime
import importlib.util
from pathlib import Path

import pytest

from trading_system.models.gc_tree_gate_baseline import build_gc_tree_gate_baseline_audit

ROOT = Path(__file__).resolve().parents[2]
_ROW_SPEC = importlib.util.spec_from_file_location(
    "gc_normalized_model_stability_fixture",
    ROOT / "tests/models/test_gc_normalized_model_stability.py",
)
if _ROW_SPEC is None or _ROW_SPEC.loader is None:
    raise RuntimeError("row fixture could not be loaded")
_ROW_MODULE = importlib.util.module_from_spec(_ROW_SPEC)
_ROW_SPEC.loader.exec_module(_ROW_MODULE)
row = _ROW_MODULE.row

FIXED_TIME = datetime(2026, 9, 7, 23, 0, tzinfo=UTC)


def tree_gap_review() -> dict:
    return {
        "review_id": "a" * 64,
        "review_version": "gc-tree-translation-gap-review-0.1.0",
        "dataset_id": "fixture-gc-dataset",
        "variant": "order_flow",
        "status": "TREE_TRANSLATION_REDESIGN_REQUIRED",
        "additional_model_training_allowed": False,
        "model_promotion_allowed": False,
    }


def candidate_rows() -> list:
    eligible = row(
        "eligible-long",
        "TARGET_FIRST",
        "TEST",
        index=1,
        direction="LONG",
        ret_1=0.05,
        of_delta=8.0,
        close=1000.0,
        atr_14=4.0,
    )
    rejected = replace(
        row(
            "rejected-short",
            "STOP_FIRST",
            "TEST",
            index=2,
            direction="SHORT",
            ret_1=-0.05,
            of_delta=-8.0,
            close=1000.0,
            atr_14=4.0,
        ),
        candidate_status="REJECTED",
        included_in_training=False,
        label_quality="EXCLUDED_FROM_TRAINING",
        exclusion_reasons=("TEST_REJECTION",),
    )
    return [eligible, rejected]


def test_tree_gate_baseline_audits_all_stages_and_waits_on_unknown_tree_gates():
    audit = build_gc_tree_gate_baseline_audit(
        candidate_rows(),
        tree_gap_review(),
        created_at=FIXED_TIME,
    ).to_payload()

    assert audit["status"] == "TREE_GATE_BASELINE_AUDIT_READY"
    assert audit["additional_model_training_allowed"] is False
    assert audit["model_promotion_allowed"] is False
    assert audit["source_tree_gap_review_id"] == "a" * 64
    assert len(audit["gate_catalog"]) == 14
    assert audit["aggregate_counts"]["rows_evaluated"] == 2
    assert audit["aggregate_counts"]["final_actions"]["WAIT"] == 1
    assert audit["aggregate_counts"]["final_actions"]["NO_TRADE"] == 1
    assert audit["stage_summary"]["VECTOR"]["UNKNOWN"] == 1
    assert audit["stage_summary"]["DATA"]["BLOCK"] == 1
    assert audit["sample_traces"][0]["final_action"] == "WAIT"
    assert audit["sample_traces"][0]["gate_path"][0]["stage"] == "DATA"
    assert audit["sample_traces"][0]["gate_path"][7]["status"] == "UNKNOWN"
    assert audit["recommended_next_phase"] == "PHASE_58_TYPED_TREE_GATE_IMPLEMENTATION"
    assert "TRAIN_ADDITIONAL_FLAT_MODEL" in audit["blocked_actions"]


def test_tree_gate_baseline_schema_rejects_model_promotion_allowed():
    run = build_gc_tree_gate_baseline_audit(
        candidate_rows(),
        tree_gap_review(),
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["model_promotion_allowed"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()

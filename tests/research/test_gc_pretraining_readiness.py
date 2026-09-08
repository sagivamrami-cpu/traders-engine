import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_pretraining_readiness_report.schema.json"
CONTRACT_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CHECKLIST_PATH = ROOT / "configs/research/real-data-readiness-checklist.yaml"
TRAINING_POLICY_PATH = ROOT / "configs/models/baseline-training-policy.yaml"
CREATED_AT = datetime(2026, 9, 1, 18, 45, tzinfo=UTC)
DATASET_ID = "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966"


def validate_gc_pretraining_readiness_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def minimal_valid_pretraining_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "report_version": "gc-pretraining-readiness-report-0.1.0",
        "mode": "GC_PRETRAINING_READINESS",
        "created_at": "2026-09-01T18:45:00Z",
        "status": "BLOCKED",
        "canonical_symbol": "GC",
        "candidate_timeframe": "30m",
        "dataset_contract_id": "gc-30m-real-dataset-contract",
        "dataset_contract_status": "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED",
        "real_data_readiness_status": "BLOCKED",
        "real_data_satisfied_count": 6,
        "real_data_open_count": 1,
        "training_policy_version": "baseline-training-policy-0.1.0",
        "training_start_allowed": False,
        "dataset_construction_allowed": True,
        "model_promotion_allowed": False,
        "required_pretraining_gates": [
            "REAL_DATASET_NOT_BUILT",
            "GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING",
        ],
        "blocked_actions": [
            "BUILD_CVD_FEATURES",
            "USE_ARCHIVED_CVD_COLUMN",
            "INGEST_PRECOMPUTED_CVD",
            "BUILD_MACRO_FEATURES",
            "USE_REVISED_MACRO_SERIES",
            "QUERY_OPTIONS_DATA",
            "INGEST_ORDERFLOW_4H_CSV",
            "JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS",
            "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
            "MAP_GC_TO_XAUUSD",
            "MAP_GC_TO_GLD",
            "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
            "TRAIN_PRODUCTION_MODEL",
            "CLAIM_EDGE",
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
        ],
        "blocking_reviews": ["GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING"],
        "human_decision_request": "agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md",
        "pending_process_steps": [
            "PROCESS_PHASE24_EXTERNAL_REVIEWS",
            "BUILD_IDENTIFIED_REAL_DATASET",
            "EVALUATE_TRAINING_READINESS",
        ],
        "build_manifest_ref": None,
        "built_dataset_id": None,
        "training_readiness": None,
    }


def test_gc_pretraining_schema_accepts_blocked_payload():
    payload = minimal_valid_pretraining_payload()
    validate_gc_pretraining_readiness_payload(payload)
    assert payload["training_start_allowed"] is False
    assert "REAL_DATASET_NOT_BUILT" in payload["required_pretraining_gates"]


def test_gc_pretraining_schema_never_allows_model_promotion():
    payload = minimal_valid_pretraining_payload()
    payload["model_promotion_allowed"] = True
    try:
        validate_gc_pretraining_readiness_payload(payload)
    except Exception:
        return
    raise AssertionError("model promotion must never validate as allowed")


def test_gc_pretraining_report_blocks_until_contract_and_reviews_are_clear():
    from trading_system.research.gc_pretraining_readiness import (
        build_gc_pretraining_readiness_report,
    )

    payload = build_gc_pretraining_readiness_report(
        contract_path=CONTRACT_PATH,
        decisions_path=DECISIONS_PATH,
        checklist_path=CHECKLIST_PATH,
        training_policy_path=TRAINING_POLICY_PATH,
        created_at=CREATED_AT,
        groq_phase24_review_path=None,
    ).to_payload()

    validate_gc_pretraining_readiness_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["training_start_allowed"] is False
    assert payload["dataset_construction_allowed"] is True
    assert payload["dataset_contract_status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert "MISSING_BAR_POLICY" not in payload["required_pretraining_gates"]
    assert "DATASET_IDENTITY" not in payload["required_pretraining_gates"]
    assert "DATASET_CONSTRUCTION_AUTHORIZATION" not in payload["required_pretraining_gates"]
    assert "BUILD_REAL_DATASET" not in payload["blocked_actions"]
    assert "TRAIN_PRODUCTION_MODEL" in payload["blocked_actions"]
    assert "BUILD_IDENTIFIED_REAL_DATASET" in payload["pending_process_steps"]
    assert payload["real_data_readiness_status"] == "BLOCKED"
    assert payload["real_data_satisfied_count"] == 6
    assert payload["real_data_open_count"] == 1
    assert "ORDER_FLOW_SOURCE_DECISION" not in payload["required_pretraining_gates"]
    assert "ROLL_POLICY" not in payload["required_pretraining_gates"]
    assert "LABEL_CONTRACT" not in payload["required_pretraining_gates"]
    assert "SPLIT_AND_EMBARGO_POLICY" not in payload["required_pretraining_gates"]
    assert "SESSION_CALENDAR" not in payload["required_pretraining_gates"]
    assert "ORDER_FLOW_ERA_MAP" not in payload["required_pretraining_gates"]
    assert "CUMULATIVE_FEATURE_POLICY" not in payload["required_pretraining_gates"]
    assert "TIMESTAMP_ROLE" not in payload["required_pretraining_gates"]
    assert "BAR_BOUNDARY" not in payload["required_pretraining_gates"]
    assert "AVAILABLE_AT_POLICY" not in payload["required_pretraining_gates"]
    assert "CANONICAL_OHLCV_INPUT" not in payload["required_pretraining_gates"]
    assert "REAL_DATASET_NOT_BUILT" in payload["required_pretraining_gates"]
    assert "GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING" in payload["blocking_reviews"]
    assert "USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"]
    assert "INGEST_PRECOMPUTED_CVD" in payload["blocked_actions"]
    assert "MAP_GC_TO_XAUUSD" in payload["blocked_actions"]
    assert "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES" in payload["blocked_actions"]
    assert "allowed_next_actions" not in payload
    assert "COLLECT_HUMAN_GATE_DECISIONS" not in payload["pending_process_steps"]
    assert "EVALUATE_TRAINING_READINESS" in payload["pending_process_steps"]


def test_gc_pretraining_requires_codex_intake_to_clear_groq_review_blocker(tmp_path: Path):
    from trading_system.research.gc_pretraining_readiness import (
        build_gc_pretraining_readiness_report,
    )

    review_dir = tmp_path / "agent-exchange/reviews"
    review_dir.mkdir(parents=True)
    review_path = review_dir / "2026-09-01T190500Z-groq-review-phase-24-dataset-contract.md"
    review_path.write_text(
        """# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Request:
`agent-exchange/inbox/groq/2026-09-01T132801Z-groq-review-phase-24-dataset-contract.md`

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT
""",
        encoding="utf-8",
    )
    intake_dir = tmp_path / "agent-exchange/status"
    intake_dir.mkdir(parents=True)
    intake_path = intake_dir / "2026-09-01T191000Z-codex-phase-24-groq-review-intake.md"
    intake_path.write_text(
        f"""# Agent Exchange Status

Sender:
Codex

Status:
ACCEPTED_BY_CODEX

Review:
{review_path.as_posix()}
""",
        encoding="utf-8",
    )

    review_only_payload = build_gc_pretraining_readiness_report(
        contract_path=CONTRACT_PATH,
        decisions_path=DECISIONS_PATH,
        checklist_path=CHECKLIST_PATH,
        training_policy_path=TRAINING_POLICY_PATH,
        created_at=CREATED_AT,
        groq_phase24_review_path=review_path,
        groq_phase24_intake_path=None,
    ).to_payload()

    assert "GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING" in review_only_payload["blocking_reviews"]

    payload = build_gc_pretraining_readiness_report(
        contract_path=CONTRACT_PATH,
        decisions_path=DECISIONS_PATH,
        checklist_path=CHECKLIST_PATH,
        training_policy_path=TRAINING_POLICY_PATH,
        created_at=CREATED_AT,
        groq_phase24_review_path=review_path,
        groq_phase24_intake_path=intake_path,
    ).to_payload()

    assert "GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING" not in payload["blocking_reviews"]
    assert "GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING" not in payload["required_pretraining_gates"]
    assert "PROCESS_PHASE24_EXTERNAL_REVIEWS" not in payload["pending_process_steps"]


def _write_trainable_build(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "market-data/gc-30m-real" / DATASET_ID[:16]
    dataset_dir.mkdir(parents=True)
    rows = pd.DataFrame(
        [
            {
                "dataset_id": DATASET_ID,
                "dataset_version": "gc-30m-real-dataset-builder-0.1.0",
                "candidate_id": f"candidate-{idx}",
                "bar_start": pd.Timestamp(f"2026-09-0{idx}T00:00:00Z"),
                "bar_end": pd.Timestamp(f"2026-09-0{idx}T00:30:00Z"),
                "direction": "LONG",
                "split": split,
                "included_ohlcv_only": True,
                "included_order_flow": True,
                "outcome_class": outcome,
                "label_quality": "HIGH",
                "exclusion_reasons_ohlcv_only": "",
                "exclusion_reasons_order_flow": "",
                "close": 1000.0 + idx,
                "atr_14": 4.0,
                "ret_1": 0.001,
                "ret_4": 0.002,
                "ret_8": 0.003,
                "ret_14": 0.004,
                "range_over_atr": 1.0,
                "volume_30m": 100,
                "seconds_with_trades": 120,
                "of_volume": 100,
                "of_delta": 1,
                "of_trades": 3,
                "of_minutes_present": 3,
                "of_volume_sum_14": 1400,
                "of_delta_sum_14": 14,
                "of_trades_sum_14": 42,
            }
            for idx, (split, outcome) in enumerate(
                [
                    ("TRAIN", "TARGET_FIRST"),
                    ("TRAIN", "STOP_FIRST"),
                    ("TRAIN", "STOP_FIRST"),
                    ("VALIDATION", "STOP_FIRST"),
                    ("TEST", "TARGET_FIRST"),
                ],
                start=1,
            )
        ]
    )
    rows_path = dataset_dir / "rows.parquet"
    rows.to_parquet(rows_path, index=False)
    manifest = {
        "manifest_id": "a" * 64,
        "manifest_version": "gc-30m-real-dataset-build-manifest-0.1.0",
        "mode": "GC_REAL_DATASET_BUILD",
        "created_at": "2026-09-07T13:00:00Z",
        "dataset_id": DATASET_ID,
        "dataset_name": "gc-30m-real-research-dataset",
        "identity_manifest_id": "b" * 64,
        "identity_source": "LOCAL_ARCHIVE_VERIFIED",
        "builder_version": "gc-30m-real-dataset-builder-0.1.0",
        "feature_schema_version": "gc-30m-real-feature-schema-0.1.0",
        "label_version": "gc-outcome-contract-label-0.1.0",
        "contract_version": "gc-atr14-1r-1r-8bar-zero-cost-0.1.0",
        "authorization_record_refs": [
            "agent-exchange/decisions/2026-09-02T162000Z-human-d9-final-dataset-construction-authorization-gc-30m-f9d3c1b0.md"
        ],
        "source_hashes": {"ohlcv_1s_zip": "c" * 64, "order_flow_zip": "d" * 64},
        "ohlcv_source_stats": {"members_read": 1, "source_rows_1s": 5, "bars_30m_with_data": 5},
        "order_flow_source_stats": {
            "member": "gc/GCext_of_1m.parquet",
            "source_rows_1m": 5,
            "bars_30m_with_order_flow": 5,
        },
        "rows_file": "rows.parquet",
        "rows_relative_dir": DATASET_ID[:16],
        "rows_sha256": sha256_file(rows_path),
        "rows_count": len(rows),
        "rows_columns": list(rows.columns),
        "summary": {
            "expected_session_bars": 5,
            "present_session_bars": 5,
            "missing_expected_bars": 0,
            "missing_expected_bars_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
            "missing_expected_bars_by_trade_date": {},
            "rows_total": len(rows),
            "rows_by_split": {"TRAIN": 3, "VALIDATION": 1, "TEST": 1},
            "variants": {
                "ohlcv_only": {
                    "included_rows": 5,
                    "excluded_rows": 0,
                    "included_rows_by_split": {"TRAIN": 3, "VALIDATION": 1, "TEST": 1},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
                    "excluded_rows_by_reason": {},
                    "excluded_rows_by_reason_and_split": {},
                    "included_outcome_class_counts": {"TARGET_FIRST": 2, "STOP_FIRST": 3},
                },
                "order_flow": {
                    "included_rows": 5,
                    "excluded_rows": 0,
                    "included_rows_by_split": {"TRAIN": 3, "VALIDATION": 1, "TEST": 1},
                    "excluded_rows_by_split": {"TRAIN": 0, "VALIDATION": 0, "TEST": 0},
                    "excluded_rows_by_reason": {},
                    "excluded_rows_by_reason_and_split": {},
                    "included_outcome_class_counts": {"TARGET_FIRST": 2, "STOP_FIRST": 3},
                },
            },
            "out_of_session_bars_with_data": 0,
            "straddle_bars": 0,
            "straddle_bars_with_data": 0,
            "first_bar_start": "2026-09-01T00:00:00Z",
            "last_bar_start": "2026-09-05T00:00:00Z",
            "rules": {"builder_version": "gc-30m-real-dataset-builder-0.1.0"},
        },
        "contract_identity_status": "UNDECLARED_PENDING_RESEARCH",
        "real_dataset_built": True,
        "training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
    }
    manifest_path = tmp_path / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, tmp_path / "market-data/gc-30m-real"


def test_gc_pretraining_readiness_becomes_ready_after_valid_build_manifest(tmp_path: Path):
    from trading_system.research.gc_pretraining_readiness import (
        build_gc_pretraining_readiness_report,
    )

    manifest_path, rows_root = _write_trainable_build(tmp_path)
    payload = build_gc_pretraining_readiness_report(
        contract_path=CONTRACT_PATH,
        decisions_path=DECISIONS_PATH,
        checklist_path=CHECKLIST_PATH,
        training_policy_path=TRAINING_POLICY_PATH,
        created_at=CREATED_AT,
        groq_phase24_review_path=ROOT / "agent-exchange/reviews/2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md",
        groq_phase24_intake_path=ROOT / "agent-exchange/status/2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md",
        build_manifest_path=manifest_path,
        rows_root=rows_root,
        variant="order_flow",
    ).to_payload()

    validate_gc_pretraining_readiness_payload(payload)
    assert payload["status"] == "READY"
    assert payload["training_start_allowed"] is True
    assert payload["built_dataset_id"] == DATASET_ID
    assert payload["required_pretraining_gates"] == []
    assert "REAL_DATASET_NOT_BUILT" not in payload["required_pretraining_gates"]
    assert "TRAIN_PRODUCTION_MODEL" not in payload["blocked_actions"]
    assert payload["training_readiness"]["variant"] == "order_flow"
    assert payload["training_readiness"]["ready"] is True
    assert payload["training_readiness"]["split_summary"]["TRAIN"] == 3
    assert payload["model_promotion_allowed"] is False


def test_gc_pretraining_readiness_blocks_when_rows_hash_does_not_match_manifest(tmp_path: Path):
    from trading_system.research.gc_pretraining_readiness import (
        build_gc_pretraining_readiness_report,
    )

    manifest_path, rows_root = _write_trainable_build(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rows_sha256"] = "e" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    payload = build_gc_pretraining_readiness_report(
        contract_path=CONTRACT_PATH,
        decisions_path=DECISIONS_PATH,
        checklist_path=CHECKLIST_PATH,
        training_policy_path=TRAINING_POLICY_PATH,
        created_at=CREATED_AT,
        groq_phase24_review_path=ROOT / "agent-exchange/reviews/2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md",
        groq_phase24_intake_path=ROOT / "agent-exchange/status/2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md",
        build_manifest_path=manifest_path,
        rows_root=rows_root,
        variant="order_flow",
    ).to_payload()

    validate_gc_pretraining_readiness_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["training_start_allowed"] is False
    assert "BUILD_MANIFEST_INVALID_OR_ROWS_UNREADABLE" in payload["required_pretraining_gates"]


def test_gc_pretraining_cli_outputs_sanitized_blocked_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_pretraining_readiness.py",
            "--contract",
            "configs/datasets/gc-30m-real-dataset-contract.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
            "--checklist",
            "configs/research/real-data-readiness-checklist.yaml",
            "--training-policy",
            "configs/models/baseline-training-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_gc_pretraining_readiness_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["training_start_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""


def test_train_gc_majority_baseline_cli_help_is_available():
    result = subprocess.run(
        [sys.executable, "tools/train_gc_majority_baseline.py", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "--build-manifest" in result.stdout
    assert "--variant" in result.stdout
    assert "--run-out" in result.stdout
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

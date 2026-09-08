import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_real_dataset_contract.schema.json"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CREATED_AT = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)
DATASET_ID = "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966"
AUTHORIZATION_REF = (
    "agent-exchange/decisions/2026-09-02T162000Z-human-d9-final-dataset-construction-authorization-gc-30m-f9d3c1b0.md"
)


def validate_gc_real_dataset_contract_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def minimal_valid_contract_payload() -> dict:
    required_gates: list[str] = []
    blocked_actions = [
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
        "MODEL_PROMOTION",
        "LIVE_TRADING",
        "BROKER_EXECUTION",
        "CAPITAL_ALLOCATION",
    ]
    return {
        "contract_report_id": "a" * 64,
        "contract_version": "gc-real-dataset-contract-0.1.0",
        "mode": "GC_REAL_DATASET_CONTRACT",
        "created_at": "2026-09-01T18:00:00Z",
        "status": "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED",
        "contract_id": "gc-30m-real-dataset-contract",
        "canonical_symbol": "GC",
        "candidate_timeframe": "30m",
        "timeframe_status": "BASELINE_APPROVED_V1_NOT_MODEL_FINAL",
        "interval_semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
        "source_decisions": {
            "ohlcv_decisions": "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
            "order_flow_source_decision": "APPROVED_RESEARCH_ORDER_FLOW_SOURCE_V1",
            "order_flow_source_decision_ref": (
                "agent-exchange/decisions/2026-09-02T052003Z-human-d6-final-order-flow-source-decision.md"
            ),
            "options_source_decision": "DEFERRED_TO_V2_DO_NOT_QUERY",
        },
        "canonical_ohlcv_input": {
            "status": "CANONICAL_OHLCV_INPUT_RECORDED_NOT_DATASET_AUTHORIZED",
            "manifest_ref": "configs/data/gc-canonical-ohlcv-input-manifest.yaml",
            "archive_sha256": "b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1",
        },
        "canonical_order_flow_input": {
            "status": "CANONICAL_ORDER_FLOW_INPUT_RECORDED_NOT_SOURCE_AUTHORIZED",
            "manifest_ref": "configs/data/gc-canonical-order-flow-input-manifest.yaml",
            "archive_sha256": "34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155",
            "selected_member": "gc/GCext_of_1m.parquet",
        },
        "session_calendar": {
            "status": "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md",
            "source_strategy_ref": "configs/data/gc-session-calendar-source-strategy.yaml",
            "construction_policy_ref": "configs/data/gc-session-calendar-construction-policy.yaml",
            "calendar_id": "cme-globex-metals-research-v1",
            "calendar_ref": "configs/data/session-calendar.yaml#cme-globex-metals-research-v1",
            "databento_status_skip_decision_ref": (
                "agent-exchange/decisions/2026-09-02T061500Z-human-d2-final-databento-status-schema-skip.md"
            ),
            "normal_session_status": "CME_GLOBEX_METALS_NORMAL_HOURS_REGISTERED_V1",
            "historical_special_hours_status": "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1",
        },
        "bar_boundary": {
            "status": "APPROVED_V1_NOT_DATASET_AUTHORIZED",
            "decision_ref": "agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md",
            "interval": "30m_UTC_FIXED_BASELINE_APPROVED_V1",
            "timezone": "UTC_FIXED_APPROVED_V1",
            "available_at": "BAR_END_UTC_APPROVED_V1",
        },
        "timestamp_role": {
            "status": "APPROVED_V1_NOT_DATASET_AUTHORIZED",
            "decision_ref": "agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md",
            "required_inputs": {
                "ohlcv_1s": "TS_EVENT_INTERVAL_START_APPROVED_V1",
                "order_flow_minute_column": "MINUTE_START_APPROVED_V1",
                "naive_order_flow_minute_timezone": "LOCALIZE_AS_UTC_WALL_CLOCK_APPROVED_V1",
            },
            "phase23_dependency": "timestamp_column_by_file",
        },
        "available_at_policy": {
            "status": "APPROVED_V1_NOT_DATASET_AUTHORIZED",
            "decision_ref": "agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md",
            "policy": "BAR_END_UTC_APPROVED_V1",
            "non_closed_bar_feature_policy": "UNDEFINED_BLOCKED_PENDING_NEW_HUMAN_DECISION",
        },
        "missing_bar_policy": {
            "status": "SATISFIED_FAIL_CLOSED_EXCLUSION_V1",
            "policy_decision_refs": [
                "agent-exchange/decisions/2026-09-01T171000Z-human-d4-missing-bar-policy-only.md",
                "agent-exchange/decisions/2026-09-02T052001Z-human-d4-final-missing-bar-policy.md",
            ],
            "policy_ref": "configs/data/gc-missing-bar-policy.yaml",
            "implementation_module": "trading_system.research.gc_real_dataset_builder",
            "family_status": {
                "ohlcv": "FAIL_CLOSED_EXCLUSION_IMPLEMENTED_V1",
                "order_flow_volume_delta_trades": "FAIL_CLOSED_EXCLUSION_IMPLEMENTED_V1",
                "order_flow_cvd_family": "FORBIDDEN_NOT_A_FEATURE_FAMILY",
            },
            "gap_detection_blocked_until": [],
            "future_manifest_requirements": [
                "ONE_RECORDED_DROP_OR_MARK_POLICY_PER_FEATURE_FAMILY",
                "EXCLUDED_OR_MARKED_ROW_COUNTS_BY_SPLIT",
                "EXCLUDED_ROW_COUNTS_BY_REASON_AND_SPLIT",
                "MISSING_EXPECTED_BAR_COUNTS_BY_SPLIT",
                "MISSING_EXPECTED_BAR_COUNTS_BY_TRADE_DATE",
            ],
            "required_scope": ["OHLCV", "ORDER_FLOW_VOLUME_DELTA_TRADES", "ORDER_FLOW_CVD_FAMILY"],
        },
        "roll_policy": {
            "status": "SATISFIED_RESEARCH_ONLY_UNDECLARED_CONTRACT_IDENTITY_V1",
            "contract_identity": "UNDECLARED_PENDING_RESEARCH",
            "policy_decision_refs": [
                "agent-exchange/decisions/2026-09-02T052002Z-human-d5-final-roll-policy-contract-identity.md"
            ],
            "blocker_status": "RESEARCH_CAVEAT_RECORDED_NOT_EXECUTION_TRUTH",
            "continuous_or_stitched_gc_policy": "PROFILE_STYLE_SANITIZED_AGGREGATES_ONLY_NON_INGESTABLE",
            "model_card_contract_identity_status": "UNDECLARED_PENDING_RESEARCH",
        },
        "order_flow_era_map": {
            "status": "SATISFIED_ROW_LEVEL_MASK_POLICY_ONLY",
            "policy_ref": "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml",
            "required_mask_function": (
                "trading_system.research.gc_order_flow_row_mask_cumulative_policy."
                "apply_gc_order_flow_training_mask"
            ),
            "required_before": ["BUILD_ORDER_FLOW_FEATURES", "BUILD_REAL_DATASET"],
            "known_damaged_aggressor_window": {
                "start": "2017-01-01T00:00:00Z",
                "end": "2017-06-01T00:00:00Z",
                "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
                "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES",
            },
        },
        "cumulative_feature_policy": {
            "status": "SATISFIED_NO_CVD_OR_CUMULATIVE_CARRY_V1",
            "policy_ref": "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml",
            "allowed_feature_families": ["VOLUME", "DELTA", "TRADES"],
            "blocked_feature_families": ["CVD", "CUMULATIVE_DELTA"],
        },
        "reference_inputs": {
            "orderflow_4h_csv": "REFERENCE_ONLY_DO_NOT_INGEST",
            "hhll_files": "AUXILIARY_ONLY_DO_NOT_USE_AS_TRADE_CONTRACT_LABEL",
        },
        "macro_features": {"status": "BLOCKED_PENDING_PER_SOURCE_DECISION_AND_LEAKAGE_GATE"},
        "options_features": {"status": "DEFERRED_TO_V2_DO_NOT_QUERY"},
        "label_contract": {
            "status": "SATISFIED_OUTCOME_CONTRACT_LABEL_V1",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052004Z-human-d7-final-label-contract.md",
            "primary_label_family": "OUTCOME_CONTRACT_LABEL",
            "risk_unit": "ATR_14_30M_CLOSED_BARS_AT_DECISION",
            "target_multiple": 1.0,
            "stop_multiple": 1.0,
            "max_horizon_bars": 8,
            "entry_availability": "NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE",
            "same_bar_target_stop_policy": "AMBIGUOUS_EXCLUDED_FROM_TRAINING",
            "hhll_role": "AUXILIARY_REFERENCE_ONLY_NOT_PRIMARY_LABEL",
            "fill_truth_status": "ZERO_COST_RESEARCH_SIMULATOR_ONLY_NOT_EXECUTION_TRUTH",
        },
        "split_and_embargo_policy": {
            "status": "SATISFIED_CHRONOLOGICAL_WALK_FORWARD_EMBARGO_V1",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052005Z-human-d8-final-split-embargo-policy.md",
            "split_method": "CHRONOLOGICAL_WALK_FORWARD_ONLY",
            "random_split_allowed": False,
            "purge_overlapping_labels": True,
            "embargo_bars": 8,
            "fold_fit_scope": "FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW",
            "damaged_2017_mask_policy": "APPLY_IDENTICALLY_TO_ALL_DATASET_AND_MODEL_VARIANTS",
        },
        "dataset_identity": {
            "status": "SATISFIED_DETERMINISTIC_IDENTITY_V1",
            "required_components": [
                "INPUT_ARCHIVE_SHA256S",
                "CONFIG_HASHES",
                "SOURCE_PROFILE_HASHES",
                "DETERMINISTIC_DATASET_ID",
            ],
            "identity_config_ref": "configs/datasets/gc-30m-real-dataset-identity.yaml",
            "identity_manifest_ref": "configs/datasets/gc-30m-real-dataset-identity-manifest.json",
            "dataset_id": DATASET_ID,
            "identity_source": "LOCAL_ARCHIVE_VERIFIED",
            "contract_identity_status": "UNDECLARED_PENDING_RESEARCH",
        },
        "dataset_construction_allowed": True,
        "training_allowed": False,
        "construction_authorized_by": [AUTHORIZATION_REF],
        "required_unsatisfied_gates": required_gates,
        "blocked_actions": blocked_actions,
        "allowed_next_actions": ["BUILD_IDENTIFIED_REAL_DATASET"],
        "blocked_reasons": [],
    }


def test_gc_real_dataset_contract_config_is_fail_closed():
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["contract_id"] == "gc-30m-real-dataset-contract"
    assert contract["contract_version"] == "gc-real-dataset-contract-0.1.0"
    assert contract["canonical_symbol"] == "GC"
    assert contract["candidate_timeframe"] == "30m"
    assert contract["timeframe_status"] == "BASELINE_APPROVED_V1_NOT_MODEL_FINAL"
    # One identified dataset build is authorized (D9-final); training is not.
    assert contract["dataset_construction_allowed"] is True
    assert contract["training_allowed"] is False
    assert contract["construction_authorized_by"] == [AUTHORIZATION_REF]
    assert contract["dataset_identity"]["dataset_id"] == DATASET_ID
    assert contract["interval_semantics"] == "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE"
    assert contract["required_unsatisfied_gates"] == []
    assert "BUILD_REAL_DATASET" not in contract["blocked_actions"]
    assert "TRAIN_PRODUCTION_MODEL" in contract["blocked_actions"]
    record = (ROOT / AUTHORIZATION_REF).read_text(encoding="utf-8")
    assert "Decision: APPROVED" in record
    assert DATASET_ID in record


def test_gc_real_dataset_contract_schema_accepts_authorized_payload():
    payload = minimal_valid_contract_payload()
    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert payload["dataset_construction_allowed"] is True
    assert payload["training_allowed"] is False
    assert payload["construction_authorized_by"] == [AUTHORIZATION_REF]
    assert "ORDER_FLOW_ERA_MAP" not in payload["required_unsatisfied_gates"]


def test_gc_real_dataset_contract_schema_never_allows_training():
    payload = minimal_valid_contract_payload()
    payload["training_allowed"] = True
    with pytest.raises(Exception):
        validate_gc_real_dataset_contract_payload(payload)


def _contract_copy(tmp_path: Path, **overrides) -> Path:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract.update(overrides)
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return path


def _tmp_root_with_record(tmp_path: Path, text: str) -> tuple[Path, str]:
    root = tmp_path / "root"
    ref = "agent-exchange/decisions/2026-09-02T000000Z-human-test-authorization.md"
    (root / ref).parent.mkdir(parents=True)
    (root / ref).write_text(text, encoding="utf-8")
    return root, ref


def test_gc_real_dataset_contract_blocks_when_authorization_record_is_invalid(tmp_path: Path):
    from trading_system.research.gc_real_dataset_contract import build_gc_real_dataset_contract_report

    # Missing record file.
    root, ref = _tmp_root_with_record(tmp_path, "Decision: APPROVED\n" + DATASET_ID)
    contract = _contract_copy(tmp_path, construction_authorized_by=["agent-exchange/decisions/missing.md"])
    payload = build_gc_real_dataset_contract_report(contract, DECISIONS_PATH, created_at=CREATED_AT, root=root).to_payload()
    assert payload["status"] == "BLOCKED"
    assert payload["dataset_construction_allowed"] is False
    assert any(reason.startswith("AUTHORIZATION_RECORD_MISSING") for reason in payload["blocked_reasons"])
    assert "BUILD_REAL_DATASET" in payload["blocked_actions"]

    # Record exists but does not bind the dataset id.
    root, ref = _tmp_root_with_record(tmp_path / "b", "Decision: APPROVED\nno id here\n")
    contract = _contract_copy(tmp_path / "b", construction_authorized_by=[ref])
    payload = build_gc_real_dataset_contract_report(contract, DECISIONS_PATH, created_at=CREATED_AT, root=root).to_payload()
    assert payload["status"] == "BLOCKED"
    assert any(reason.startswith("AUTHORIZATION_RECORD_DOES_NOT_BIND_DATASET_ID") for reason in payload["blocked_reasons"])

    # Record is not approved.
    root, ref = _tmp_root_with_record(tmp_path / "c", "Decision: NOT_APPROVED\n" + DATASET_ID)
    contract = _contract_copy(tmp_path / "c", construction_authorized_by=[ref])
    payload = build_gc_real_dataset_contract_report(contract, DECISIONS_PATH, created_at=CREATED_AT, root=root).to_payload()
    assert any(reason.startswith("AUTHORIZATION_RECORD_NOT_APPROVED") for reason in payload["blocked_reasons"])

    # Construction enabled while a gate is still open.
    root, ref = _tmp_root_with_record(tmp_path / "d", "Decision: APPROVED\n" + DATASET_ID)
    contract = _contract_copy(
        tmp_path / "d", construction_authorized_by=[ref], required_unsatisfied_gates=["MISSING_BAR_POLICY"]
    )
    payload = build_gc_real_dataset_contract_report(contract, DECISIONS_PATH, created_at=CREATED_AT, root=root).to_payload()
    assert payload["status"] == "BLOCKED"
    assert "CONSTRUCTION_ENABLED_WHILE_GATES_UNSATISFIED" in payload["blocked_reasons"]

    # Valid record under a temp root -> authorized.
    root, ref = _tmp_root_with_record(tmp_path / "e", "Decision: APPROVED\n" + DATASET_ID)
    contract = _contract_copy(tmp_path / "e", construction_authorized_by=[ref])
    payload = build_gc_real_dataset_contract_report(contract, DECISIONS_PATH, created_at=CREATED_AT, root=root).to_payload()
    assert payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert payload["construction_authorized_by"] == [ref]
    assert payload["allowed_next_actions"] == ["BUILD_IDENTIFIED_REAL_DATASET"]


def test_gc_real_dataset_contract_report_is_construction_authorized_and_training_blocked():
    from trading_system.research.gc_real_dataset_contract import (
        build_gc_real_dataset_contract_report,
    )

    report = build_gc_real_dataset_contract_report(
        CONTRACT_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    )
    payload = report.to_payload()

    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert payload["blocked_reasons"] == []
    assert payload["required_unsatisfied_gates"] == []
    assert payload["construction_authorized_by"] == [AUTHORIZATION_REF]
    assert payload["allowed_next_actions"] == ["BUILD_IDENTIFIED_REAL_DATASET"]
    assert payload["training_allowed"] is False
    assert "BUILD_REAL_DATASET" not in payload["blocked_actions"]
    assert "TRAIN_PRODUCTION_MODEL" in payload["blocked_actions"]
    assert "MODEL_PROMOTION" in payload["blocked_actions"]
    assert payload["dataset_identity"]["status"] == "SATISFIED_DETERMINISTIC_IDENTITY_V1"
    assert payload["dataset_identity"]["dataset_id"] == DATASET_ID
    assert payload["source_decisions"]["order_flow_source_decision"] == (
        "APPROVED_RESEARCH_ORDER_FLOW_SOURCE_V1"
    )
    assert payload["source_decisions"]["order_flow_source_decision_ref"].endswith(
        "human-d6-final-order-flow-source-decision.md"
    )
    assert payload["source_decisions"]["options_source_decision"] == "DEFERRED_TO_V2_DO_NOT_QUERY"
    assert payload["canonical_ohlcv_input"]["status"] == "CANONICAL_OHLCV_INPUT_RECORDED_NOT_DATASET_AUTHORIZED"
    assert payload["canonical_ohlcv_input"]["archive_sha256"] == "b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1"
    assert payload["canonical_order_flow_input"]["status"] == (
        "CANONICAL_ORDER_FLOW_INPUT_RECORDED_NOT_SOURCE_AUTHORIZED"
    )
    assert payload["canonical_order_flow_input"]["archive_sha256"] == (
        "34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155"
    )
    assert payload["canonical_order_flow_input"]["selected_member"] == "gc/GCext_of_1m.parquet"
    assert payload["session_calendar"]["status"] == "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH"
    assert payload["session_calendar"]["decision_ref"].endswith("human-d2-final-session-calendar-implementation.md")
    assert payload["session_calendar"]["construction_policy_ref"] == "configs/data/gc-session-calendar-construction-policy.yaml"
    assert payload["session_calendar"]["calendar_id"] == "cme-globex-metals-research-v1"
    assert payload["session_calendar"]["calendar_ref"] == "configs/data/session-calendar.yaml#cme-globex-metals-research-v1"
    assert payload["session_calendar"]["databento_status_skip_decision_ref"].endswith(
        "human-d2-final-databento-status-schema-skip.md"
    )
    assert payload["order_flow_era_map"]["status"] == "SATISFIED_ROW_LEVEL_MASK_POLICY_ONLY"
    assert payload["order_flow_era_map"]["policy_ref"] == (
        "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml"
    )
    assert payload["order_flow_era_map"]["required_mask_function"] == (
        "trading_system.research.gc_order_flow_row_mask_cumulative_policy."
        "apply_gc_order_flow_training_mask"
    )
    assert payload["cumulative_feature_policy"]["status"] == "SATISFIED_NO_CVD_OR_CUMULATIVE_CARRY_V1"
    assert payload["cumulative_feature_policy"]["allowed_feature_families"] == ["VOLUME", "DELTA", "TRADES"]
    assert payload["bar_boundary"]["status"] == "APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert payload["available_at_policy"]["status"] == "APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert payload["available_at_policy"]["non_closed_bar_feature_policy"] == (
        "UNDEFINED_BLOCKED_PENDING_NEW_HUMAN_DECISION"
    )
    assert payload["timestamp_role"]["phase23_dependency"] == "timestamp_column_by_file"
    assert payload["timestamp_role"]["status"] == "APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert payload["timestamp_role"]["decision_ref"].endswith("human-d3-timestamp-policy-v1.md")
    assert payload["dataset_construction_allowed"] is True
    assert "BAR_BOUNDARY" not in payload["required_unsatisfied_gates"]
    assert "SESSION_CALENDAR" not in payload["required_unsatisfied_gates"]
    assert "AVAILABLE_AT_POLICY" not in payload["required_unsatisfied_gates"]
    assert "TIMESTAMP_ROLE" not in payload["required_unsatisfied_gates"]
    assert "DATASET_IDENTITY" not in payload["required_unsatisfied_gates"]
    assert "MISSING_BAR_POLICY" not in payload["required_unsatisfied_gates"]
    assert "DATASET_CONSTRUCTION_AUTHORIZATION" not in payload["required_unsatisfied_gates"]
    assert "CANONICAL_OHLCV_INPUT" not in payload["required_unsatisfied_gates"]
    assert "CANONICAL_ORDER_FLOW_INPUT" not in payload["required_unsatisfied_gates"]
    assert "ORDER_FLOW_SOURCE_DECISION" not in payload["required_unsatisfied_gates"]
    assert "USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"]
    assert "INGEST_PRECOMPUTED_CVD" in payload["blocked_actions"]
    assert "MAP_GC_TO_XAUUSD" in payload["blocked_actions"]
    assert "MAP_GC_TO_GLD" in payload["blocked_actions"]
    assert "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES" in payload["blocked_actions"]
    assert payload["missing_bar_policy"]["status"] == "SATISFIED_FAIL_CLOSED_EXCLUSION_V1"
    assert payload["missing_bar_policy"]["family_status"]["ohlcv"] == "FAIL_CLOSED_EXCLUSION_IMPLEMENTED_V1"
    assert payload["missing_bar_policy"]["family_status"]["order_flow_cvd_family"] == "FORBIDDEN_NOT_A_FEATURE_FAMILY"
    assert payload["missing_bar_policy"]["policy_ref"] == "configs/data/gc-missing-bar-policy.yaml"
    assert payload["session_calendar"]["historical_special_hours_status"] == (
        "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1"
    )
    assert payload["roll_policy"]["status"] == "SATISFIED_RESEARCH_ONLY_UNDECLARED_CONTRACT_IDENTITY_V1"
    assert payload["roll_policy"]["contract_identity"] == "UNDECLARED_PENDING_RESEARCH"
    assert payload["roll_policy"]["model_card_contract_identity_status"] == "UNDECLARED_PENDING_RESEARCH"
    assert payload["label_contract"]["status"] == "SATISFIED_OUTCOME_CONTRACT_LABEL_V1"
    assert payload["label_contract"]["risk_unit"] == "ATR_14_30M_CLOSED_BARS_AT_DECISION"
    assert payload["label_contract"]["target_multiple"] == 1.0
    assert payload["label_contract"]["stop_multiple"] == 1.0
    assert payload["label_contract"]["max_horizon_bars"] == 8
    assert payload["split_and_embargo_policy"]["status"] == "SATISFIED_CHRONOLOGICAL_WALK_FORWARD_EMBARGO_V1"
    assert payload["split_and_embargo_policy"]["embargo_bars"] == 8
    assert "ROLL_POLICY" not in payload["required_unsatisfied_gates"]
    assert "LABEL_CONTRACT" not in payload["required_unsatisfied_gates"]
    assert "SPLIT_AND_EMBARGO_POLICY" not in payload["required_unsatisfied_gates"]


def test_gc_real_dataset_contract_accepts_approved_order_flow_decision(tmp_path: Path):
    from trading_system.research.gc_real_dataset_contract import (
        build_gc_real_dataset_contract_report,
    )

    decisions = tmp_path / "decisions.yaml"
    temp_decisions_dir = tmp_path / "agent-exchange/decisions"
    shutil.copytree(DECISIONS_PATH.parent, temp_decisions_dir)
    (temp_decisions_dir / "2026-09-01T180000Z-human-order-flow-approved-test.md").write_text(
        """# Human Decision

Approver: Human Data Owner

Created at: 2026-09-01T18:00:00Z

Scope: invalid test approval

Decision: APPROVED

Evidence: test-only valid human decision record
""",
        encoding="utf-8",
    )
    decisions = temp_decisions_dir / "decisions.yaml"
    decisions.write_text(
        (temp_decisions_dir / DECISIONS_PATH.name).read_text(encoding="utf-8")
        + """
  - item_id: ORDER_FLOW_SOURCE_DECISION
    decision: APPROVED
    approver: Human Data Owner
    decided_at: "2026-09-01T18:00:00Z"
    scope: invalid test approval
    evidence:
      - agent-exchange/decisions/2026-09-01T180000Z-human-order-flow-approved-test.md
""",
        encoding="utf-8",
    )

    payload = build_gc_real_dataset_contract_report(
        CONTRACT_PATH,
        decisions,
        created_at=CREATED_AT,
    ).to_payload()

    assert payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert "ORDER_FLOW_SOURCE_DECISION_MUST_REMAIN_OPEN_FOR_CONTRACT_ONLY_PHASE" not in payload["blocked_reasons"]
    assert payload["dataset_construction_allowed"] is True
    assert payload["training_allowed"] is False


def test_gc_real_dataset_contract_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_real_dataset_contract.py",
            "--contract",
            "configs/datasets/gc-30m-real-dataset-contract.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    assert payload["training_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/research/gc-label-split-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_label_split_policy.schema.json"
CREATED_AT = datetime(2026, 9, 1, 22, 0, tzinfo=UTC)


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def minimal_valid_label_split_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "policy_version": "gc-label-split-policy-0.1.0",
        "mode": "GC_LABEL_SPLIT_POLICY",
        "created_at": "2026-09-01T22:00:00Z",
        "status": "APPROVED_LABEL_SPLIT_CONTRACTS_DATASET_CONSTRUCTION_AUTHORIZED",
        "canonical_symbol": "GC",
        "candidate_timeframe": "30m_UTC_FIXED_BASELINE_APPROVED_V1",
        "label_contract_policy": {
            "status": "SATISFIED_OUTCOME_CONTRACT_LABEL_V1",
            "d7_decision_status": "APPROVED_DECISION_RECORDED",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052004Z-human-d7-final-label-contract.md",
            "primary_label_family": "OUTCOME_CONTRACT_LABEL",
            "hhll_role": "AUXILIARY_DIRECTION_LABEL_ONLY_NOT_TRAINING_TARGET",
            "hhll_auxiliary_training_status": "BLOCKED_PENDING_SEPARATE_PIT_LABEL_STUDY",
            "future_only_outcome_required": True,
            "same_bar_target_and_stop_policy": "AMBIGUOUS_EXCLUDED_FROM_TRAINING",
            "ambiguous_label_quality_requirement": "LABEL_QUALITY_EXCLUDED_FROM_TRAINING_REQUIRED",
            "binary_projection_status": "AMBIGUOUS_ROWS_EXCLUDED_BEFORE_BINARY_PROJECTION",
            "risk_unit": "ATR_14_30M_CLOSED_BARS_AT_DECISION",
            "target_multiple": 1.0,
            "stop_multiple": 1.0,
            "max_horizon_bars": 8,
            "entry_availability": "NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE",
            "target_stop_threshold_status": "SPECIFIED_ATR14_1R_TARGET_1R_STOP",
            "horizon_status": "SPECIFIED_8_BARS_30M",
            "fill_truth_status": "ZERO_COST_RESEARCH_SIMULATOR_ONLY_NOT_EXECUTION_TRUTH",
            "allowed_outcome_classes": [
                "TARGET_FIRST",
                "STOP_FIRST",
                "EXPIRED",
                "AMBIGUOUS",
            ],
        },
        "split_and_embargo_policy": {
            "status": "SATISFIED_CHRONOLOGICAL_WALK_FORWARD_EMBARGO_V1",
            "d8_decision_status": "APPROVED_DECISION_RECORDED",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052005Z-human-d8-final-split-embargo-policy.md",
            "split_method": "CHRONOLOGICAL_WALK_FORWARD_ONLY",
            "random_split_allowed": False,
            "purging_required": True,
            "embargo_required": True,
            "embargo_size_status": "SPECIFIED_8_BARS_MATCHES_MAX_LABEL_HORIZON",
            "embargo_bars": 8,
            "purge_rule_status": "PURGE_OVERLAPPING_8_BAR_LABEL_HORIZON",
            "fold_fit_scope": "FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW",
            "damaged_2017_mask_policy": "APPLY_IDENTICALLY_TO_ALL_DATASET_AND_MODEL_VARIANTS",
            "row_level_2017_mask_status": "SATISFIED_SHARED_ORDER_FLOW_MASK_FUNCTION",
            "required_mask_function": (
                "trading_system.research.gc_order_flow_row_mask_cumulative_policy."
                "apply_gc_order_flow_training_mask"
            ),
            "ohlcv_only_vs_order_flow_scope_status": "APPLY_TO_ALL_DATASET_VARIANTS",
            "known_damaged_aggressor_window": {
                "start": "2017-01-01T00:00:00Z",
                "end": "2017-06-01T00:00:00Z",
                "semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
                "status": "EXCLUDE_FROM_ORDER_FLOW_FEATURES_AND_ALL_SPLIT_VARIANTS",
            },
        },
        "dataset_construction_allowed": True,
        "label_building_allowed": True,
        "split_building_allowed": True,
        "training_allowed": False,
        "required_remaining_gates": [],
        "blocked_actions": [
            "TRAIN_PRODUCTION_MODEL",
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
            "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
            "CLAIM_EDGE",
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
        ],
        "blocked_reasons": [],
    }


def test_gc_label_split_policy_schema_accepts_authorized_payload():
    payload = minimal_valid_label_split_payload()
    validate_policy_payload(payload)
    assert payload["label_contract_policy"]["primary_label_family"] == "OUTCOME_CONTRACT_LABEL"
    assert payload["label_contract_policy"]["d7_decision_status"] == "APPROVED_DECISION_RECORDED"
    assert payload["label_contract_policy"]["hhll_role"].endswith("NOT_TRAINING_TARGET")
    assert payload["label_contract_policy"]["hhll_auxiliary_training_status"].startswith("BLOCKED")
    assert payload["label_contract_policy"]["ambiguous_label_quality_requirement"] == (
        "LABEL_QUALITY_EXCLUDED_FROM_TRAINING_REQUIRED"
    )
    assert payload["split_and_embargo_policy"]["random_split_allowed"] is False
    assert payload["split_and_embargo_policy"]["d8_decision_status"] == "APPROVED_DECISION_RECORDED"
    assert payload["split_and_embargo_policy"]["fold_fit_scope"] == (
        "FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW"
    )
    assert payload["split_and_embargo_policy"]["row_level_2017_mask_status"] == "SATISFIED_SHARED_ORDER_FLOW_MASK_FUNCTION"
    assert payload["dataset_construction_allowed"] is True
    assert payload["training_allowed"] is False


def test_gc_label_split_policy_schema_never_allows_training():
    payload = minimal_valid_label_split_payload()
    payload["training_allowed"] = True
    try:
        validate_policy_payload(payload)
    except Exception:
        return
    raise AssertionError("training must never validate as allowed by the label/split policy")


def test_gc_label_split_policy_config_and_report_are_construction_authorized():
    from trading_system.research.gc_label_split_policy import build_gc_label_split_policy_report

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["label_contract_policy"]["primary_label_family"] == "OUTCOME_CONTRACT_LABEL"
    assert config["label_contract_policy"]["d7_decision_status"] == "APPROVED_DECISION_RECORDED"
    assert config["label_contract_policy"]["hhll_role"] == (
        "AUXILIARY_DIRECTION_LABEL_ONLY_NOT_TRAINING_TARGET"
    )
    assert config["label_contract_policy"]["hhll_auxiliary_training_status"] == (
        "BLOCKED_PENDING_SEPARATE_PIT_LABEL_STUDY"
    )
    assert config["label_contract_policy"]["same_bar_target_and_stop_policy"] == (
        "AMBIGUOUS_EXCLUDED_FROM_TRAINING"
    )
    assert config["split_and_embargo_policy"]["split_method"] == "CHRONOLOGICAL_WALK_FORWARD_ONLY"
    assert config["split_and_embargo_policy"]["random_split_allowed"] is False
    assert config["split_and_embargo_policy"]["embargo_required"] is True
    assert config["split_and_embargo_policy"]["embargo_size_status"] == "SPECIFIED_8_BARS_MATCHES_MAX_LABEL_HORIZON"
    assert config["split_and_embargo_policy"]["fold_fit_scope"] == (
        "FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW"
    )
    assert config["split_and_embargo_policy"]["row_level_2017_mask_status"] == "SATISFIED_SHARED_ORDER_FLOW_MASK_FUNCTION"

    payload = build_gc_label_split_policy_report(
        CONFIG_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    assert payload["status"] == "APPROVED_LABEL_SPLIT_CONTRACTS_DATASET_CONSTRUCTION_AUTHORIZED"
    assert payload["label_building_allowed"] is True
    assert payload["split_building_allowed"] is True
    assert payload["dataset_construction_allowed"] is True
    assert payload["training_allowed"] is False
    assert payload["required_remaining_gates"] == []
    assert payload["blocked_reasons"] == []
    assert "BUILD_REAL_LABELS" not in payload["blocked_actions"]
    assert "MISSING_BAR_POLICY" not in payload["required_remaining_gates"]
    assert "DATASET_CONSTRUCTION_AUTHORIZATION" not in payload["required_remaining_gates"]
    assert "LABEL_CONTRACT" not in payload["required_remaining_gates"]
    assert "SPLIT_AND_EMBARGO_POLICY" not in payload["required_remaining_gates"]
    assert "SESSION_CALENDAR" not in payload["required_remaining_gates"]
    assert "GRAPH_TRADE_CONTRACT" not in payload["required_remaining_gates"]
    assert "COST_FILL_POLICY" not in payload["required_remaining_gates"]
    assert "ROW_LEVEL_2017_MASK" not in payload["required_remaining_gates"]
    assert "BAR_BOUNDARY" not in payload["required_remaining_gates"]
    assert "TIMESTAMP_ROLE" not in payload["required_remaining_gates"]
    assert "AVAILABLE_AT_POLICY" not in payload["required_remaining_gates"]
    assert "USE_HHLL_AS_TRADE_CONTRACT_LABEL" in payload["blocked_actions"]
    assert "INGEST_HHLL_DERIVED_LABELS" in payload["blocked_actions"]
    assert "USE_HHLL_AS_AUXILIARY_TRAINING_TARGET" in payload["blocked_actions"]
    assert "ADAPT_FIXTURE_TRADE_CONTRACT_TO_REAL_GC" in payload["blocked_actions"]
    assert "RANDOM_SPLIT_TIME_SERIES_ROWS" in payload["blocked_actions"]
    assert "BUILD_UNEMBARGOED_SPLITS" in payload["blocked_actions"]
    assert "TARGET_STOP_THRESHOLDS_UNSPECIFIED" not in payload["blocked_reasons"]
    assert "MAX_LABEL_HORIZON_UNSPECIFIED" not in payload["blocked_reasons"]
    assert "EMBARGO_SIZE_UNSPECIFIED" not in payload["blocked_reasons"]
    assert "ROW_LEVEL_2017_MASK_NOT_IMPLEMENTED" not in payload["blocked_reasons"]
    assert "C:\\" not in json.dumps(payload, sort_keys=True)


def test_gc_label_split_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_label_split_policy.py",
            "--policy",
            "configs/research/gc-label-split-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_policy_payload(payload)
    assert payload["status"] == "APPROVED_LABEL_SPLIT_CONTRACTS_DATASET_CONSTRUCTION_AUTHORIZED"
    assert payload["training_allowed"] is False
    assert payload["split_and_embargo_policy"]["damaged_2017_mask_policy"] == (
        "APPLY_IDENTICALLY_TO_ALL_DATASET_AND_MODEL_VARIANTS"
    )
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""


def test_gc_label_split_policy_schema_rejects_hhll_primary_training_target():
    payload = minimal_valid_label_split_payload()
    payload["label_contract_policy"]["primary_label_family"] = "HHLL_DIRECTION_LABEL"

    try:
        validate_policy_payload(payload)
    except Exception as exc:
        assert "OUTCOME_CONTRACT_LABEL" in str(exc)
    else:
        raise AssertionError("HHLL primary labels must not validate")


def test_gc_label_split_policy_schema_rejects_random_split():
    payload = minimal_valid_label_split_payload()
    payload["split_and_embargo_policy"]["random_split_allowed"] = True

    try:
        validate_policy_payload(payload)
    except Exception as exc:
        assert "False was expected" in str(exc) or "false" in str(exc).lower()
    else:
        raise AssertionError("random split must not validate")

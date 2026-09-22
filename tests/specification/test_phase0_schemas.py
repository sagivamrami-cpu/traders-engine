import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def assert_valid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def assert_invalid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert errors


def test_feature_value_valid_contract():
    assert_valid(
        "feature_value.schema.json",
        {
            "name": "tr.vector.recovery_pct",
            "value": 0.48,
            "dtype": "float",
            "status": "VALID",
            "observed_at": "2026-08-30T12:42:00Z",
            "computed_at": "2026-08-30T12:42:01Z",
            "source": "market-feed-v2",
            "engine_version": "vector-engine-1.0.0",
            "confidence": 0.91,
        },
    )


def test_feature_value_rejects_unknown_null_semantics():
    assert_invalid(
        "feature_value.schema.json",
        {
            "name": "tr.vector.recovery_pct",
            "value": 0,
            "dtype": "float",
            "status": "UNKNOWN",
            "observed_at": "2026-08-30T12:42:00Z",
            "computed_at": "2026-08-30T12:42:01Z",
            "source": "market-feed-v2",
            "engine_version": "vector-engine-1.0.0",
            "confidence": 0.91,
        },
    )


def test_unified_market_state_valid_contract():
    assert_valid(
        "unified_market_state.schema.json",
        {
            "snapshot_id": "ums-GC-20260830T124200Z",
            "symbol": "GC",
            "observation_time": "2026-08-30T12:42:00Z",
            "schema_version": "ums-1.0.0",
            "data_quality": "VALID",
            "feature_values": {},
            "availability": {"tr": True, "order_flow": True, "options": False},
            "regime": {
                "primary": "EXPANSION",
                "probabilities": {
                    "TREND": 0.31,
                    "RANGE": 0.09,
                    "EXPANSION": 0.56,
                    "EVENT": 0.04,
                },
            },
        },
    )


def test_candidate_action_valid_contract():
    assert_valid(
        "candidate_action.schema.json",
        {
            "candidate_id": "c-001",
            "snapshot_id": "ums-GC-20260830T124200Z",
            "producer": "TR",
            "graph_id": "tr-vshape-retest-long",
            "graph_version": "1.0.0",
            "direction": "LONG",
            "status": "ELIGIBLE",
            "created_at": "2026-08-30T12:42:00Z",
            "expires_at": "2026-08-30T13:02:00Z",
            "reasons": ["V_SHAPE_COMPLETE", "RETEST_CONFIRMED"],
        },
    )


def test_trade_contract_valid_contract():
    assert_valid(
        "trade_contract.schema.json",
        {
            "contract_version": "tr-contract-1.0.0",
            "entry_policy": "TRIGGER_CLOSE",
            "entry_price": 2410.0,
            "stop_policy": "STRUCTURE_INVALIDATION",
            "stop_price": 2400.0,
            "target_policy": "NEXT_NAMED_LEVEL",
            "target_price": 2432.0,
            "expiry_policy": "MAX_20_BARS",
            "max_holding_bars": 20,
            "commission": 2.4,
            "slippage_model_version": "slippage-1.0.0",
            "fill_policy_version": "fill-1.0.0",
        },
    )


def test_outcome_label_accepts_ambiguous():
    assert_valid(
        "outcome_label.schema.json",
        {
            "candidate_id": "c-001",
            "label_version": "outcome-1.0.0",
            "outcome_class": "AMBIGUOUS",
            "target_before_stop": 0,
            "stop_before_target": 0,
            "expired": 0,
            "net_return_r": None,
            "mae_r": -0.35,
            "mfe_r": 2.4,
            "time_to_outcome_bars": 1,
            "filled": True,
            "realized_slippage_ticks": None,
            "label_quality": "EXCLUDED_FROM_TRAINING",
        },
    )


def test_prediction_valid_contract():
    assert_valid(
        "prediction.schema.json",
        {
            "candidate_id": "c-001",
            "model_id": "candidate-outcome-gbdt",
            "model_version": "0.3.0",
            "feature_schema_version": "ums-1.0.0",
            "p_target_first": 0.74,
            "p_stop_first": 0.21,
            "p_expired": 0.05,
            "expected_net_return_r": 0.82,
            "expected_mae_r": -0.46,
            "expected_mfe_r": 1.88,
            "uncertainty": 0.09,
            "coverage_status": "IN_DISTRIBUTION",
            "calibration_version": "cal-0.2.0",
        },
    )


def test_final_decision_valid_contract():
    assert_valid(
        "final_decision.schema.json",
        {
            "decision": "LONG",
            "candidate_id": "c-001",
            "decision_policy_version": "policy-0.2.0",
            "hard_gates_passed": True,
            "expected_value_r": 0.82,
            "risk_size": 0.25,
            "reasons": [
                "POSITIVE_EXPECTED_VALUE",
                "CALIBRATED_CONFIDENCE",
                "RISK_WITHIN_LIMIT",
            ],
        },
    )


def test_llm_meta_output_rejects_order_action():
    assert_invalid(
        "llm-meta-output.schema.json",
        {
            "thesis": "looks strong",
            "supported_state_paths": ["tr.vector.recovery_pct"],
            "assumptions": [],
            "contradictions": [],
            "recommended_action": "SUBMIT_ORDER",
            "confidence": 0.61,
            "schema_version": "llm-meta-0.1.0",
        },
    )

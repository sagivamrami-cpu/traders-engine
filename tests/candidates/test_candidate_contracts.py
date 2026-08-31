import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.candidates.contracts import CandidateAction, OutcomeLabel, TradeContract

ROOT = Path(__file__).resolve().parents[2]


def validate(schema_name: str, payload: dict) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_candidate_action_payload_matches_schema():
    candidate = CandidateAction(
        candidate_id="candidate-1",
        snapshot_id="snapshot-1",
        producer="TR",
        graph_id="tr-vshape-retest-long",
        graph_version="fixture-graph-rules-0.1.0",
        direction="LONG",
        status="ELIGIBLE",
        created_at=datetime(2026, 8, 28, 13, 31, tzinfo=UTC),
        expires_at=datetime(2026, 8, 28, 13, 32, tzinfo=UTC),
        reasons=("POSITIVE_RETURN",),
    )

    validate("candidate_action.schema.json", candidate.to_payload())


def test_trade_contract_payload_matches_schema():
    contract = TradeContract(
        contract_version="fixture-tr-contract-0.1.0",
        entry_policy="FIXTURE_CLOSE_ENTRY",
        entry_price=451.0,
        stop_policy="FIXTURE_BAR_LOW",
        stop_price=450.2,
        target_policy="FIXTURE_TWO_R_TARGET",
        target_price=452.6,
        expiry_policy="FIXTURE_MAX_BARS",
        max_holding_bars=2,
        commission=0.0,
        slippage_model_version="fixture-zero-slippage-0.1.0",
        fill_policy_version="fixture-close-fill-0.1.0",
    )

    validate("trade_contract.schema.json", contract.to_payload())


def test_outcome_label_payload_matches_schema():
    label = OutcomeLabel(
        candidate_id="candidate-1",
        label_version="fixture-outcome-0.1.0",
        outcome_class="TARGET_FIRST",
        target_before_stop=1,
        stop_before_target=0,
        expired=0,
        net_return_r=2.0,
        mae_r=0.25,
        mfe_r=2.0,
        time_to_outcome_bars=1,
        filled=True,
        realized_slippage_ticks=0.0,
        label_quality="HIGH",
    )

    validate("outcome_label.schema.json", label.to_payload())

"""Fixture-only Phase 3 candidate and label factories."""

from trading_system.candidates.contracts import CandidateAction, OutcomeLabel, TradeContract
from trading_system.candidates.generation import generate_fixture_candidate
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate

__all__ = [
    "CandidateAction",
    "OutcomeLabel",
    "TradeContract",
    "build_fixture_trade_contract",
    "generate_fixture_candidate",
    "label_long_candidate",
]

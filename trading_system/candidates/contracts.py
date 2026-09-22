from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from trading_system.features.contracts import utc_iso


@dataclass(frozen=True)
class CandidateAction:
    candidate_id: str
    snapshot_id: str
    producer: str
    graph_id: str
    graph_version: str
    direction: str
    status: str
    created_at: datetime
    expires_at: datetime
    reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "snapshot_id": self.snapshot_id,
            "producer": self.producer,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "direction": self.direction,
            "status": self.status,
            "created_at": utc_iso(self.created_at),
            "expires_at": utc_iso(self.expires_at),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class TradeContract:
    contract_version: str
    entry_policy: str
    entry_price: float
    stop_policy: str
    stop_price: float
    target_policy: str
    target_price: float
    expiry_policy: str
    max_holding_bars: int
    commission: float
    slippage_model_version: str
    fill_policy_version: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "entry_policy": self.entry_policy,
            "entry_price": self.entry_price,
            "stop_policy": self.stop_policy,
            "stop_price": self.stop_price,
            "target_policy": self.target_policy,
            "target_price": self.target_price,
            "expiry_policy": self.expiry_policy,
            "max_holding_bars": self.max_holding_bars,
            "commission": self.commission,
            "slippage_model_version": self.slippage_model_version,
            "fill_policy_version": self.fill_policy_version,
        }


@dataclass(frozen=True)
class OutcomeLabel:
    candidate_id: str
    label_version: str
    outcome_class: str
    target_before_stop: int
    stop_before_target: int
    expired: int
    net_return_r: float | None
    mae_r: float | None
    mfe_r: float | None
    time_to_outcome_bars: int | None
    filled: bool
    realized_slippage_ticks: float | None
    label_quality: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "label_version": self.label_version,
            "outcome_class": self.outcome_class,
            "target_before_stop": self.target_before_stop,
            "stop_before_target": self.stop_before_target,
            "expired": self.expired,
            "net_return_r": self.net_return_r,
            "mae_r": self.mae_r,
            "mfe_r": self.mfe_r,
            "time_to_outcome_bars": self.time_to_outcome_bars,
            "filled": self.filled,
            "realized_slippage_ticks": self.realized_slippage_ticks,
            "label_quality": self.label_quality,
        }

"""Offline arithmetic for supplied, verified resolved fills, not a fill simulator.

No touch, intrabar sequence, management or evidence-authenticity inference occurs
here. The replay caller must establish causal fills. Policy values are explicit
research inputs, not market approval, and these outputs are outcome labels only.

Arithmetic uses 50 significant digits, ROUND_HALF_EVEN, and exponents -999..999.
Inputs and monetary intermediates must be exactly representable; unsupported
precision/range fails closed rather than changing the sign of net P&L. Only
net_R may round (to 50 significant digits). Caller Decimal settings are ignored.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, Inexact,
    InvalidOperation, Overflow, ROUND_HALF_EVEN, Subnormal, Underflow, localcontext,
)
import hashlib
import json


_CONTEXT = Context(
    prec=50, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999, capitals=1,
    clamp=0, flags=[],
    traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Subnormal, Inexact],
)


def _nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _instrument(value: str) -> None:
    _nonempty(value, "instrument")
    parts = value.split(":")
    if len(parts) != 2 or not all(parts) or any(c.isspace() for c in value):
        raise ValueError("instrument must be an exact venue:symbol")


def _money(value: Decimal, field: str, *, positive: bool) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{field} has an invalid sign")
    try:
        with localcontext(_CONTEXT) as context:
            context.create_decimal(value)
    except DecimalException as exc:
        raise ValueError(f"{field} exceeds supported Decimal precision/range") from exc


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware datetimes")
    return value.astimezone(timezone.utc)


def _decimal_text(value: Decimal) -> str:
    # Formatting does not use the caller's context; equivalent scales hash alike.
    if value == 0:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


@dataclass(frozen=True, kw_only=True)
class EconomicPolicy:
    """Explicit position economics; commission is currency per entire side.

    commission_per_side is the total charge for the supplied position, not a
    per-unit fee. spread_points is the total round-trip mid-price deduction.
    executable_fills already contain spread/slippage, so both must be zero.
    """

    policy_id: str
    instrument: str
    currency: str
    point_value: Decimal
    quantity: Decimal
    commission_per_side: Decimal
    spread_points: Decimal
    slippage_points_per_side: Decimal
    pending_expiry_seconds: int
    max_holding_seconds: int
    fill_rule: str
    simultaneous_rule: str
    cost_basis: str
    provenance: str

    def __post_init__(self) -> None:
        for field in ("policy_id", "currency", "provenance"):
            _nonempty(getattr(self, field), field)
        _instrument(self.instrument)
        for field in ("point_value", "quantity"):
            _money(getattr(self, field), field, positive=True)
        for field in ("commission_per_side", "spread_points", "slippage_points_per_side"):
            _money(getattr(self, field), field, positive=False)
        for field in ("pending_expiry_seconds", "max_holding_seconds"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field} must be a positive integer")
        if self.fill_rule != "supplied_verified_fills":
            raise ValueError("fill_rule must be supplied_verified_fills")
        if self.simultaneous_rule not in ("ambiguous", "stop_first"):
            raise ValueError("unsupported simultaneous_rule")
        if self.cost_basis not in ("mid_price_plus_costs", "executable_fills"):
            raise ValueError("unsupported cost_basis")
        if self.cost_basis == "executable_fills" and (
            self.spread_points != 0 or self.slippage_points_per_side != 0
        ):
            raise ValueError("executable_fills requires zero spread and slippage costs")


@dataclass(frozen=True, kw_only=True)
class ResolvedTrade:
    """Supplied full-position exit evidence; no price is inferred or simulated."""

    candidate_id: str
    instrument: str
    direction: str
    decision_time: datetime
    filled_at: datetime
    exited_at: datetime
    available_at: datetime
    entry_price: Decimal
    initial_stop: Decimal
    tp1: Decimal
    exit_price: Decimal
    exit_reason: str
    evidence: str

    def __post_init__(self) -> None:
        _nonempty(self.candidate_id, "candidate_id")
        _nonempty(self.evidence, "evidence")
        _instrument(self.instrument)
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError("direction must be LONG or SHORT")
        if self.exit_reason not in ("TP1", "STOP", "TIME_EXIT", "INVALIDATION"):
            raise ValueError("exit_reason must identify a resolved full exit")
        for field in ("entry_price", "initial_stop", "tp1", "exit_price"):
            _money(getattr(self, field), field, positive=True)
        if self.direction == "LONG":
            geometry = self.initial_stop < self.entry_price < self.tp1
        else:
            geometry = self.tp1 < self.entry_price < self.initial_stop
        if not geometry:
            raise ValueError("initial stop and TP1 must bracket entry in trade direction")
        for field in ("decision_time", "filled_at", "exited_at", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field)))
        if not self.decision_time <= self.filled_at <= self.exited_at <= self.available_at:
            raise ValueError("timestamps must follow decision <= fill <= exit <= availability")


def evaluate_resolved_trade(policy: EconomicPolicy, trade: ResolvedTrade) -> dict:
    """Compute fixed-risk economic outcomes; caller proves actual event causality.

    Pending expiry is exclusive; the holding limit is inclusive from fill time.
    Same-instant events are accepted when supplied with evidence. This chronology
    check cannot establish which price was touched first within a bar.
    """
    if not isinstance(policy, EconomicPolicy) or not isinstance(trade, ResolvedTrade):
        raise ValueError("explicit EconomicPolicy and ResolvedTrade are required")
    if policy.instrument != trade.instrument:
        raise ValueError("policy/trade instrument mismatch; no venue or symbol mapping")
    # Integer microseconds avoid float loss and timedelta overflow for durations.
    pending_us = (trade.filled_at - trade.decision_time) // timedelta(microseconds=1)
    holding_us = (trade.exited_at - trade.filled_at) // timedelta(microseconds=1)
    if pending_us >= policy.pending_expiry_seconds * 1_000_000:
        raise ValueError("fill must precede the pending expiry deadline")
    if holding_us > policy.max_holding_seconds * 1_000_000:
        raise ValueError("exit exceeds the maximum holding horizon")

    try:
        with localcontext(_CONTEXT) as context:
            units = policy.point_value * policy.quantity
            risk = (trade.entry_price - trade.initial_stop).copy_abs() * units
            direction = 1 if trade.direction == "LONG" else -1
            gross = direction * (trade.exit_price - trade.entry_price) * units
            cost = 2 * policy.commission_per_side
            if policy.cost_basis == "mid_price_plus_costs":
                cost += (policy.spread_points + 2 * policy.slippage_points_per_side) * units
            net = gross - cost
            context.traps[Inexact] = False  # Ratios can be nonterminating.
            net_r = net / risk
            values = dict(gross_pnl=gross, total_cost=cost, net_pnl=net, initial_risk=risk, net_R=net_r)
            if not all(value.is_finite() for value in values.values()):
                raise ValueError("nonfinite economic arithmetic")
    except DecimalException as exc:
        raise ValueError("economic arithmetic exceeds supported Decimal precision/range") from exc

    canonical_policy = {
        key: _decimal_text(value) if isinstance(value, Decimal) else value
        for key, value in asdict(policy).items()
    }
    encoded = json.dumps(canonical_policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "candidate_id": trade.candidate_id,
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "instrument": policy.instrument,
        "economic_label": "SUCCESS" if net > 0 else "FAILURE" if net < 0 else "BREAK_EVEN",
        **{key: _decimal_text(value) for key, value in values.items()},
        "currency": policy.currency,
        "label_end_time": trade.exited_at.isoformat().replace("+00:00", "Z"),
        "available_at": trade.available_at.isoformat().replace("+00:00", "Z"),
        "provenance": policy.provenance,
        "evidence": trade.evidence,
    }

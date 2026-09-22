## Task 2: Explicit economic policy and resolved-outcome arithmetic (delegated)

Files: create only `trading_system/tree_spec/economics.py` and `tests/tree_spec/test_economics.py`; own report under agent-exchange/status.

Interface design (use frozen dataclasses, keyword-only fields to avoid argument mistakes):

```python
@dataclass(frozen=True, kw_only=True)
class EconomicPolicy:
    policy_id: str
    instrument: str             # exact venue:symbol, no automatic mapping
    currency: str
    point_value: Decimal        # currency / one price-point / one quantity unit
    quantity: Decimal
    commission_per_side: Decimal
    spread_points: Decimal     # total round-trip mid-price spread deduction
    slippage_points_per_side: Decimal
    pending_expiry_seconds: int
    max_holding_seconds: int
    fill_rule: str              # 'supplied_verified_fills'
    simultaneous_rule: str      # 'ambiguous' or 'stop_first'
    cost_basis: str             # 'mid_price_plus_costs' or 'executable_fills'
    provenance: str             # explicit source/assumption record, synthetic in tests

@dataclass(frozen=True, kw_only=True)
class ResolvedTrade:
    candidate_id: str
    instrument: str
    direction: str              # 'LONG' or 'SHORT'
    decision_time: datetime
    filled_at: datetime
    exited_at: datetime
    available_at: datetime
    entry_price: Decimal
    initial_stop: Decimal
    tp1: Decimal
    exit_price: Decimal
    exit_reason: str            # 'TP1', 'STOP', 'TIME_EXIT', 'INVALIDATION'
    evidence: str

def evaluate_resolved_trade(policy: EconomicPolicy, trade: ResolvedTrade) -> dict:
    ...
```

- [ ] Write tests first, run RED. Missing constructor fields must fail; reject None/bool/float/string for Decimal money fields, nonfinite or invalid sign values, blank IDs/provenance, nonpositive/bool durations, unsupported modes, naive/future-order timestamps, venue mismatch, wrong geometry, entry at/after pending deadline, exit beyond maximum holding horizon, and unsupported outcomes (unfilled/ambiguous cannot be resolved).
- [ ] Implement explicit, validated policy only (no defaults). Initial risk = abs(entry_price-initial_stop)*point_value*quantity, fixed across outcomes. Gross P&L = signed(exit-entry)*point_value*quantity. Mid-price costs = 2*commission_per_side + (spread_points+2*slippage_points_per_side)*point_value*quantity. For executable_fills require spread/slippage components ==0 to avoid double charging; commission still applies. Commission is the total currency amount per side for the supplied position, not per unit; document it.
- [ ] Compute net_P&L/net_R with Decimal (bounded deterministic local decimal context), classify exact positive/negative/zero, serialize monetary outputs as decimal strings. Reject nonfinite arithmetic. Do not infer movement success from exit P&L, do not infer fill prices or create trades. Same-instant exits are allowed with supplied evidence; this is chronology validation, not proof of intrabar sequence.
- [ ] Return candidate/policy identity, economic_label, gross_pnl, total_cost, net_pnl, initial_risk, net_R, currency, label_end_time=exited_at, available_at, provenance and a stable policy SHA256. Normalize datetimes to UTC before comparisons and serialization, including DST folds. No binary failure probability and no invented trade-signal score.
- [ ] Literal tests: long 100->104, stop98, quantity2, point_value10, commission1/side, spread0.1, slippage0.05/side => gross80, cost6, net74, risk40, net_R1.85. Short mirror matches. A target exit can be net-negative after costs. Zero P&L is BREAK_EVEN. Changed costs change policy identity. External caller decimal precision must not change output.
- [ ] Run `python -m pytest tests/tree_spec/test_economics.py -q`, self-review, report RED/GREEN and changed paths. No commits, no subagents, no outside files.

This function evaluates supplied settled evidence; it does NOT validate that TP1/STOP was truly touched or simulate fills/management. The caller must obtain causal verified events from the next replay phase. Arbitrary supplied data passing structural validation is not proof of profitable trades.


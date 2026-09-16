# Offline source reversal pricing

`trading_system.tree_replay.pricing.price_reversals_asof` connects the closed-bar
reversal detector to the original planned entry, stop and target calculation.
It does not admit, execute or score a trade. The live alert system is unchanged.

## Interface and inputs

```python
from trading_system.tree_replay.pricing import price_reversals_asof

result = price_reversals_asof(
    closed_bars, snapshot_id="evaluation-reference",
    instrument="OANDA:XAUUSD", timeframe="5m",
    decision_time=decision_time, history_start=history_start,
    max_age_seconds=bar_age_budget, level_snapshot=level_state,
    max_level_age_seconds=level_age_budget,
    # session_schedule=explicit_schedule,
)
```

The variables above must come from caller-supplied historical evidence and
explicit freshness policies, as documented in LEVEL-REVERSAL-ASOF-USAGE.md.
No defaults invent freshness, missing data, instrument conversion or session
coverage. Only the latest selected closed confirmation is evaluated. Input
generators are materialized once; detection and pricing use the same window.

Pricing supports the source producer identities `OANDA:XAUUSD`,
`OANDA:NAS100USD`, and `BINANCE:BTCUSDT`. A detected setup in another identity
returns BLOCKED / PRICING_UNSUPPORTED_INSTRUMENT; its geometry is not invented.
In particular, GC futures do not acquire OANDA spot-gold rules through an alias.
This is an adapter coverage boundary, not a new rule in the live tree.

All supplied levels participate in pricing, not just detector-eligible anchors.
Repeated display names at different prices need distinct explicit `level_id`
values. This preserves source maps containing multiple Q-QUARTER locations.
Duplicate IDs or duplicate name/price pairs remain errors. Source order remains
the tie-break order. The detector adapter version is now v2 because serialized
level evidence includes IDs: old evaluation hashes are not interchangeable with
new ones. Candidate event identity and numerical detection logic are unchanged.

## What the output means

- Input BLOCKED and NO_CANDIDATE retain their meanings; neither is a losing trade.
- On pricing completion, top-level status is PRICING_EVALUATED.
- Each candidate has source_plan and a separate pre-entry pricing_snapshot.
- PRICE_ACCEPTED_UNADMITTED means only that the source pricing predicate passed.
- PRICE_REFUSED preserves the original geometry, obstacles and refusal reason.
- Candidate tradeable stays false and trade_plan stays null in all cases.
- Both ready_for_replay and ready_for_training remain false.

`source_plan` records entry, entry_zone, stop, atr, risk_price, rr_tp1, rr_far,
targets, obstacles, source_tradeable, source_direction, symbol, style, reasons,
warnings and refusal. These are planned prices, never fill prices or profits.
`pricing_snapshot` exposes the numeric geometry and counts, refusal and source
pricing predicate. Missing TP values are null / NOT_APPLICABLE. A snapshot's
eligible flag describes its own optional feature completeness, not admission.

The original detection hash is retained in detection_evaluation_sha256; the new
evaluation_sha256 also includes pricing version and source commit. The detector
hash already covers selected inputs, policies and runtime versions. Feature
availability is the maximum availability of all selected bars, level evidence
and any supplied calendar. Hashes, IDs and audit metadata are not model inputs.
Malformed/nonfinite/nonpositive pricing geometry fails closed with ValueError.

## Preserved source behavior

Source: chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
`chartdesk.tr.atr` uses unseeded exponential smoothing, not the separately
implemented indicators ATR. M5 is scalp; M15 is intraday. Stops follow the source
instrument/style bands measured from entry-zone edges and optional quarter-grid
anchoring. The anchoring ceiling comparison is preserved as written in source.

Targets inside the zone or too close by ATR are removed; nearby target levels
are merged. The first paying level must satisfy the source 1.2R threshold.
Nearer nonpaying levels are obstacles, not profit targets. When the nearest
paying level is farther than 2R, no-obstacle geometry can receive the source's
rounded 1.5R measured rung; an intervening obstacle instead yields refusal.
These values reproduce this pinned implementation, not universal trading rules.

The vendor Plan class is explicitly a projection: all original dataclass fields
and class constants, only risk/rr/rr_far/tradeable methods. Display, live and
management functionality is not claimed to be ported. Source quarter-lookup
warnings preserve the original nonblocking fallback behavior.

## Verification and remaining work

Run `python -m pytest tests/tree_replay/test_pricing_source.py
tests/tree_replay/test_pricing.py -q` and
`python tools/check_pricing_source_parity.py --source-root <retained-chart-desk>`.
The checker verifies fixed Git blobs, ordered AST subsets, exact imports and the
documented Plan projection, plus the prior detector dependency audit. It reads
source text only. Pure subset parity is not end-to-end alert or market parity.

Historical level construction, source correction evidence, admission, arbitration,
order lifecycle/fills and the approved full-TP1 economics remain separate work.
There is no new outcome dataset, trained model or measured win rate from this
component. No data acquisition, retention, live trading or deployment is approved
by this document. Full progress: TREE-OUTCOME-IMPLEMENTATION-TRACKER.md.

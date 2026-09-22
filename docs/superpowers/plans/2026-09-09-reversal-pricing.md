# Original reversal pricing implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development and TDD.

**Goal:** Connect original entry/stop/targets/refusals to as-of reversal setups,
advancing the full approved plan without claiming admission, fills or labels.
**Architecture:** Pure pinned source pricing dependencies plus an additive wrapper
that re-evaluates trusted bars/levels, never accepts a mutable candidate dict as
evidence. Preserve original detector API and its previous source checker.
**Tech Stack:** Existing Python dataclasses, pandas/numpy, pytest, AST/text audit.
**Spec:** docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md sections3-12,18;
full objective tracked in docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md.

## Global Constraints

- Existing chart-desk commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 is authoritative.
- No invented thresholds, GC/spot conversion, live source execution or alerts.
- No raw feeds, economic labels, model fitting, promotion or deployment in pricing.
- Preserve current branch and previous dirty work; no commits/worktrees/cleanup.
- Keep full goal active: this task does not complete B-I or prove profitability.

## Task 1: Pure source pricing dependencies (sidecar)

Files: new _vendor/pricing.py, _vendor/basis_symbols.py, _vendor/quarters.py,
_vendor/atr.py, _vendor/reversal_pricing.py under trading_system/tree_replay;
tools/check_pricing_source_parity.py; configs/trees/reversal-pricing-contracts.json;
tests/tree_replay/test_pricing_source.py; assigned worker report only.

Exact selected source members and imports are specified in the task brief.
Plan class is an explicit projection: all original dataclass fields and the
four original properties risk/rr/rr_far/tradeable, excluding display/live methods.
Keep its class/dataclass AST and projected members identical. Original build_plan
is copied with pure local aliases; quarter anchoring must work, not be a forced
exception fallback. Source canonical_symbol is copied, never broadened to GC.

- [x] Write and run failing synthetic tests for zones, bands, anchoring, ladder,
  measured rung, refusal, Plan properties, ATR initialization and end-to-end build.
- [x] Copy selected symbols exactly; for example original behavior must satisfy:
  `apply_stop_band('OANDA:XAUUSD', 100, 98, 2, [], style='scalp') == 93`;
  no-obstacle target130 with entry100/stop93 inserts measured TP1 at110.5;
  obstacle105 before target130 refuses far TP1 rather than inserting a rung.
- [x] Implement fixed-scope blob/AST auditor and tamper tests, including class
  projection and prior detector dependency verification; never execute source.
- [x] Run python -m pytest tests/tree_replay/test_pricing_source.py -q and source
  CLI --source-root <retained-chart-desk>. Report RED/GREEN, exact scope and gaps.

## Task 2: As-of pricing integration (parent critical path)

Create trading_system/tree_replay/pricing.py and tests/tree_replay/test_pricing.py.
Source-driven amendment: modify levels.py to accept optional explicit level_id;
duplicate display names require distinct IDs and prices, while ambiguous repeats
remain rejected. levelmap emits multiple Q-QUARTER locations; do not discard them.
Bump reversal adapter version to v2 because level-evidence serialization changes;
detector signature/numerical logic remain unchanged. Include these diffs in review.
Interface matches detector keyword arguments:
`price_reversals_asof(bars, *, snapshot_id, instrument, timeframe, decision_time,
history_start, max_age_seconds, level_snapshot, max_level_age_seconds,
session_schedule=None) -> dict`.

- [x] Write failing tests for actual 5m/15m long/short detection+pricing with source
  instruments, unsupported instruments, source refusal/obstacles/1.5R insertion,
  future/late/stale/gap blockers, deterministic hashes, generator inputs and JSON.
- [x] Materialize bars once, call existing detector, then reselect the same window
  for source build_plan. No unknown candidate payloads accepted. Reconstruct exact
  Reversal values internally; use the same full supplied level tuple for targets.
- [x] Preserve detection and input blockers. For a detected setup require an exact
  supported source instrument (OANDA:XAUUSD, OANDA:NAS100USD, BINANCE:BTCUSDT);
  otherwise PRICING_UNSUPPORTED_INSTRUMENT, without pretending GC==spot. This is
  source-coverage status, not a new live trading rule. Missing data and no setup
  remain distinct from a priced plan's refusal.
- [x] Return source_plan (entry, zone, stop, targets/obstacles, risk, rr/rr_far,
  atr, style, reasons, warnings, refusal, source_tradeable), pricing_status
  PRICE_ACCEPTED_UNADMITTED or PRICE_REFUSED, and separate pre-entry pricing
  snapshot with source/provenance. Top candidate tradeable remains false.
- [x] Fingerprint pricing version/runtime plus detection evaluation identity;
  record all dependency availability. Guard nonfinite or nonpositive planned
  prices/risks; fail closed rather than rounding or repairing source geometry.
- [x] Keep ready_for_replay/training false, no execution/lifecycle/outcome labels.
  Confirm previous detector output/behavior is unchanged.

## Task 3: Acceptance and next full-plan step

- [x] Package actual untracked diffs, independently review each task and combined
  integration; fix concrete defects and verify the exact affected behavior.
- [x] Run both new test targets, tree_replay/tree_spec/session integration, source
  CLIs, and broad suite with explicit legacy validator exclusion.
- [x] Document pricing interfaces/source quirks, update full tracker/master/memory
  and exchange acceptance. Proceed toward historical level-map construction;
  do not close the full objective merely because pricing passes.

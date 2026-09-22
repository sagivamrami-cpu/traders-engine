# Offline level-reversal detection

Continuation of the approved tree-outcome plan, not a new strategy. Work in the
existing dirty checkout; preserve all unrelated changes. No commits or deployment.

## Goal and boundary

Adapt the pinned chart-desk `level_reversal.detect_frame` into an offline,
closed-and-available-bar detector. Output is an UNPRICED setup, never an admitted
trade or a success/failure label. Do not modify the live alert system.

Source: chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
Preserve the M5 red/green two-bar and M15 red/violet/green/blue single-bar
conditions, eligible levels, sort/tie order, confirmation dedup and event IDs.
PVSRA uses only its default non-auction branch, explicitly identified as a
specialization; no seasonal/auction parameters are exposed.

## Preflight and interfaces

| Boundary | Contract | Evidence / missing work |
| --- | --- | --- |
| Bars | Existing ClosedBar and contiguous or explicit-session selector | Closed/available as of T; no duplicate revisions |
| Levels | Immutable NamedLevel and LevelSnapshot | Caller supplies exact instrument, source/version, observed/available times; historical level construction is NOT implemented |
| Detection | Vendored pure source subset | Fixed commit/blob and AST parity checks; no importing live checkout |
| Evaluation | Latest selected confirmation bar only | Do not apply one level snapshot retrospectively to earlier signals |
| Output | BLOCKED / NO_CANDIDATE / DETECTED_UNPRICED | No entry fill, stop, TP, admission, outcome, or training eligibility |

`detect_reversals_asof(bars, *, snapshot_id, instrument, timeframe, decision_time,
history_start, max_age_seconds, level_snapshot, max_level_age_seconds,
session_schedule=None)` returns a JSON-safe dictionary. Only 5m/15m supported.
Freshness budgets are caller-supplied positive integers, not invented live gates.
All levels must be observed no later than the confirmation close, available by
T, and within the explicit age budget. Missing levels/volume/history block.
Known empty or ineligible levels produce NO_CANDIDATE, not a failed trade.
All-zero volume is unavailable, never an ordinary negative detection.

Keep separate stable source-event identity and complete evaluation hash (input
bars, levels, calendar, policies, versions, decision time). Feature evidence
describes only the setup's pre-entry measurements. Dependencies' availability
must be recorded. No claim that metadata proves historical truth.

## Task 1 — Pure source sidecar

Write only `_vendor/level_reversal.py`, `_vendor/pvsra.py`,
`tools/check_reversal_source_parity.py`, `configs/trees/level-reversal-contracts.json`,
`tests/tree_replay/test_reversal_source.py`, and a scoped result note.
Test-first synthetic source cases; exact AST parity for selected detector symbols
and default-PVSRA statements. Fixed manifest coverage; fail on missing/tampered
symbols/source files. Source checkout is read-only text, never executed.

## Task 2 — As-of wrapper (parent critical path)

Write `levels.py`, `reversal.py`, and `tests/tree_replay/test_reversal.py`.
Test-first source long/short cases; missing, late, stale, future, duplicate and
cross-instrument inputs; warmup; closed/unfinished candles; level ties; latest
confirmation only; calendar histories and adjacent-pattern gap restrictions;
finite numeric/JSON boundaries and deterministic identity/provenance.

## Task 3 — Review, verification and handoff

Review sidecar and wrapper against contracts; independent combined review.
Run new tests, tree_replay/tree_spec/session integration, source parity CLI, and
the broad suite excluding previously scoped legacy validator files. State that
exclusion explicitly. Record result and usage docs, update master plan and memory.
No all-tree, dataset, profitability or trained-model completion claim.

Next: historically reproducible level-map inputs and original trade-plan pricing,
then admission/arbitration and replay economics under the approved exit contract.

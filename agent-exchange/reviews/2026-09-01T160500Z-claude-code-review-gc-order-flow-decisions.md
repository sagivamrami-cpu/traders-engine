# Agent Exchange Review

Reviewer:
Claude Code

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-01T153500Z-claude-code-review-gc-order-flow-decisions.md`

Created at:
2026-09-01T16:05:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Planning review of the seven proposed human decisions for GC order-flow
intake and first-baseline training preparation, plus the Phase 23 direction
(local order-flow ZIP intake, metadata/profile only). Review-only; no
implementation files were modified, no Databento API was called, and no raw
data was read. This review does not approve production model training, model
promotion, purchase/download, live trading, broker execution, or capital
allocation.

## Per-decision assessment

1. Order-flow ZIP as research/training-prep source: SOUND, with the Phase 14
   contract applied — it must become a formal decision record under
   `agent-exchange/decisions/` plus an `ORDER_FLOW_SOURCE_DECISION: APPROVED`
   entry in the decisions YAML whose scope says research/training-preparation
   only. Until recorded, nothing is unblocked (verified: readiness still
   reports `satisfied_count=5`, `open_count=2`, `BLOCKED`).
2. Exclude 2017-01-01..2017-05-31 for order-flow features: SOUND and
   evidence-driven, but it must be machine-enforced, not prose (C2 below).
3. `gold_orderflow_4h.csv` reference-only: SOUND. Enforce it the way HHLL
   ingest was enforced in Phase 20 — a blocked action (e.g.
   `INGEST_ORDERFLOW_4H_CSV`) plus a defined cross-check with an explicit
   tolerance, so reference disagreement is a failure, not silence (C3).
4. 30m first baseline: ACCEPTABLE and defensible (answer to focus Q2 below),
   but it contradicts a frozen contract: Phase 20's profile schema consts
   `recommended_timeframe: "4h"`. That const must be superseded explicitly
   (schema/version bump or a dedicated timeframe-decision artifact), not
   left contradicting the new decision (C4).
5. `GC.FUT`/`parent` for cost-preflight only: matches the Phase 22 gate
   exactly — but it is currently NOT EXECUTABLE: the open Phase 21/22 review
   findings (Groq F1/F2, Claude F1) mean a decision-applied online run would
   emit reports that violate the Phase 21 report schema and would still
   resolve symbology with a hardcoded `stype_in="raw_symbol"`. Those fixes
   must land before the first real-key run (C1).
6. Options deferred to v2: SOUND — record it as an explicit
   `OPTIONS_SOURCE_DECISION: DEFERRED` entry with evidence (defer is a
   recorded decision, never an omission, per the Phase 18/19 contract), and
   keep the options parent `UNCONFIRMED_DO_NOT_QUERY`.
7. Macro features behind leakage checks and ablations: DIRECTIONALLY FINE
   but underspecified — recommend narrowing it (C5): each macro feed needs
   its own source decision (vendor, licensing, and point-in-time vintage
   timestamps, since macro series are revised), so a blanket allow should
   become "macro requires a per-source decision plus leakage/ablation gate".

## Answers to the review-focus questions

- Q1 (sufficient to unblock Phase 23?): Yes, with the changes below.
  Metadata/profile-only intake mirroring the Phase 20 gate is the right
  shape, and nothing here approves production training or trading.
- Q2 (30m vs 4H/5m/1m): 30m is the best first choice. GC trades ~23h/day,
  so 30m yields roughly 45 bars/day and a six-figure sample over the
  16-year archive — enough for a baseline — while giving order-flow
  aggregates per bar that are meaningful and far less microstructure-noisy
  than 1m/5m; 4H gives too few rows for ML and spans the daily maintenance
  break awkwardly. Preconditions: the still-pending session-calendar and
  bar-boundary convention (UTC-fixed vs session-anchored) and the
  `available_at = bar_end` rule become binding at 30m and must be pinned
  before dataset construction (they are the same G1/G3 gates flagged at
  Phase 20 review).
- Q3 (Phase 23 validators/schema/tests): see C2, C6.
- Q4 (4H reference vs 1m canonical risks): timestamp-convention mismatch is
  the main trap — the CSV keys on `bar_close_utc` while the Parquet
  `ts_event` is interval start, so any cross-check must state its alignment
  rule or every comparison is off by one interval. Also keep the reference
  CSV out of the feature store entirely; its precomputed columns are a
  leakage vector if joined casually.
- Q5 (Phase 21/22 conflicts): yes, two — the unresolved GC.FUT
  schema/stype findings (C1) and the Phase 20 4h-const contradiction (C4).

## Changes required (by severity)

### C1 — HIGH: land the open Phase 21/22 review fixes before any GC.FUT run

Groq Phase 22 F1 (applied `GC.FUT` symbols are illegal under the Phase 21
report schema), F2 (`symbology.resolve` hardcodes `raw_symbol`), and Claude
Phase 22 F1 (`selected_symbols` accepts non-GC symbols) are still open — no
review intake has been recorded. Decision 5 cannot be exercised until these
land; sequencing them into Phase 23 (or a small pre-fix pass) should be
explicit.

### C2 — HIGH: machine-enforce the damaged-window exclusion

Create a committed exclusions config (instrument, feature family, interval,
reason, evidence ref), a schema, and tests asserting: order-flow feature
construction refuses 2017-01-01..2017-05-31; OHLCV-only features are
explicitly unaffected (state the boundary); and evaluation windows crossing
the exclusion apply one documented policy (mask identically for every model
variant, to keep comparisons fair). A prose-only exclusion will eventually
be missed.

### C3 — MEDIUM: enforce reference-only status of the 4H CSV

Blocked action (e.g. `INGEST_ORDERFLOW_4H_CSV`) in the Phase 23 profile
contract plus a bounded cross-check (like Phase 20's resample match) with an
explicit tolerance and alignment rule.

### C4 — MEDIUM: supersede the Phase 20 `recommended_timeframe: 4h` const

Version the Phase 20 profile schema (or add a superseding timeframe-decision
artifact that Phase 23 validates against) so the 30m decision and the frozen
4h const do not coexist as contradictory contracts.

### C5 — LOW: narrow the macro-features decision

Replace the blanket allow with: each macro source requires its own recorded
source decision (vendor, licensing, vintage/first-release timestamps with
`available_at` = release time) before any macro feature exists, in addition
to the leakage/ablation gate.

### C6 — Phase 23 additions checklist (for the plan)

- Order-flow ZIP profile module/schema/CLI/validator mirroring Phase 20:
  redacted paths, zip sha256, entry/row counts, exact column contract for
  the vendor's order-flow fields (delta/aggressor semantics recorded from
  vendor docs, never invented), timestamp-role const, no-trade policy,
  nested `source_identity`, `full_archive_quality_status`, all approval
  booleans const false, `allowed_next_actions` empty, deny-list including
  dry-run/resample/raw-copy/HHLL/4H-CSV ingest.
- Decision artifacts: order-flow APPROVED (research-prep scope) and options
  DEFERRED, both with evidence records; after recording, readiness should
  show `satisfied_count=6`, `open_count=1` (deferred stays open), status
  `BLOCKED`.
- Tests for the exclusion window, reference-only enforcement, and the
  timeframe-contract supersession.

## Commands run and results

- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  `satisfied_count=5`, `open_count=2`, status `BLOCKED` (order-flow and
  options still open — correct until the new decisions are recorded).
- `python tools/validate_phase21.py`: PASS, `Phase 21 artifacts validated`.
- `python tools/validate_databento_gc_contract_stype_decision.py`: PASS,
  prints the open template payload (`OPEN_HUMAN_DECISION`,
  `approved_for_cost_preflight: false`), exit 0.

## Blocking-issue statement

No blocking issue against the decisions themselves. C1 blocks only the
GC.FUT online usage until the open Phase 21/22 findings land; C2 must be in
the Phase 23 plan before any order-flow feature work. Verdict:
ACCEPT_WITH_CHANGES.

Notes:
- Review-only: no implementation files modified, no API calls, no raw data
  read.
- No secrets, keys, account identifiers, raw market data, or absolute local
  paths are included here.

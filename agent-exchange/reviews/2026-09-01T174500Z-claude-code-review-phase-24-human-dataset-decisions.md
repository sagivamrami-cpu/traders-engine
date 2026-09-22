# Agent Exchange Review

Reviewer:
Claude Code

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-01T131100Z-claude-code-review-phase-24-human-dataset-decisions.md`

Created at:
2026-09-01T17:45:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Review of the five human decision records dated 2026-09-01T15:38:00Z-:04Z
and their consistency with the decisions YAML, the Phase 23 quality gates,
and the planned contract-only Phase 24. Review-only; no source code was
modified, no vendor was queried, and no raw market-data rows were read.
This review does not approve feature construction, dataset construction,
training, model promotion, live trading, broker execution, or capital
allocation.

## Answers to the five questions

### 1. Are the records internally consistent?

Yes. Each record carries approver, timestamp, scope, decision, and
evidence; each is narrowed exactly as the prior Claude Code and Groq
reviews demanded, and each matches its machine-readable counterpart:
profile-only order-flow intake (record explicitly does NOT satisfy
`ORDER_FLOW_SOURCE_DECISION`, matching the YAML omission and the Phase 23
builder guard), options `DEFERRED` (matches the YAML entry), 30m as
candidate (matches `timeframe.status: RESEARCH_PARAMETER_PENDING`), the
2017 window as one measured exclusion (matches the gates config), and
macro per-source gating (matches the gates config). Verified live:
readiness reports `satisfied_count=5`, `open_count=2`, `BLOCKED`.

Two small wording gaps (C2, C3 below), neither a contradiction.

### 2. Can Codex safely implement a contract-only Phase 24?

Yes. The records give precise pending gates without authorizing any data
work. The skeleton must be schema/config/validator only: no dataset
builder entry point may exist, `dataset_construction_allowed` stays a
schema const `false`, and the contract should carry an explicitly empty
`construction_authorized_by` field that only a future human decision
record id can fill.

### 3. Fields the Phase 24 contract must require before any builder can run

1. `session_calendar`: committed calendar definition (not the pending
   sentinel).
2. `bar_boundary`: UTC-fixed vs session-anchored, with the DST rule.
3. `timestamp_role` per input: `ts_event` interval-start for OHLCV 1s;
   vendor confirmation of the order-flow `minute` column's wall-clock
   timezone (Phase 23 review L2) — assumption recorded today, proof
   required here.
4. `missing_bar_policy`: absent-row vs zero-fill semantics per feature
   family.
5. `roll_policy` and contract identity for the stitched OHLCV series
   (Phase 20 G2 — still the oldest unresolved gate).
6. `available_at` derivation rule per input (bar-window end or stricter).
7. `era_map`: full-archive schema/availability eras for order-flow
   columns — the 2017 record itself obligates this measurement "before
   any feature build", and Phase 23 sampling only partially discharges it
   (C1 below); include damaged-window boundary semantics.
8. `cumulative_feature_policy`: fold-local recompute / era-gap rules that
   would unblock CVD-family features.
9. `split_and_embargo_policy`: train/eval split rules that apply the 2017
   exclusion mask identically to every model variant.
10. `label_contract`: outcome-contract labels at the chosen timeframe
    (HHLL stays auxiliary; 4H CSV stays non-ingestable).
11. Dataset identity: input archive sha256s, config hashes, deterministic
    dataset id — so a later builder is reproducible and auditable.
12. Readiness linkage: order-flow features require a future
    `ORDER_FLOW_SOURCE_DECISION` approval; the contract should name that
    dependency explicitly.

### 4. Do any decisions need narrower wording or a separate record?

- C1 — era-map obligation placement: the 2017 record says "Phase 23 must
  measure the archive's full schema and availability eras before any
  feature build". Phase 23 as implemented samples up to five Parquet files;
  the full era map is not yet measured. No record change needed, but Phase
  24 must carry `era_map` as a required, currently-unsatisfied input so the
  obligation is not silently considered discharged.
- C2 — the "both" ambiguity (flagged per the request's Notes): repository
  state cannot show which two "clarified pending decisions" the newest
  human message approved — five records were created in the same minute.
  Minimum fix: one short human confirmation record listing, by filename,
  exactly which decision records the "both approved" message covers.
  Until then, Codex should treat the five committed records as the
  authoritative set and the chat message as non-authoritative (an inbox
  message is not approval; the records are).
- C3 — 2017 boundary semantics: the record says "through 2017-05-31"
  (inclusive end date) while the gates config encodes
  `end: 2017-06-01T00:00:00Z`. These agree only under half-open
  `[start, end)` semantics, which nothing states. One line in the Phase 24
  contract ("all exclusion intervals are half-open UTC `[start, end)`")
  resolves it; no new human record needed.

### 5. Phase 23 risks that should block Phase 24?

None blocking. The Phase 23 review (this reviewer, 2026-09-01T171500Z)
was ACCEPT with three low findings; fold L2 (naive-UTC wall-clock
confirmation) into the `timestamp_role` field and surface the
timestamp-column heuristic (L1) in a later Phase 23 revision. One
sequencing note: Groq's Phase 23 review was not yet in the exchange at
review time — Codex should intake it before Phase 23 acceptance, though
contract-skeleton drafting need not wait.

## Commands run and results

- `python tools/validate_phase23.py`: PASS, `Phase 23 artifacts validated`.
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  `satisfied_count=5`, `open_count=2`, status `BLOCKED`, with
  `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` open.

## Blocking-issue statement

No blocking issues. The changes are: the C2 confirmation record (minimum
one short human record naming the approved set), the C3 interval-semantics
line, and carrying C1's era-map as a required unsatisfied Phase 24 input.
Verdict: ACCEPT_WITH_CHANGES.

Notes:
- Review-only: no code modified, no vendor queried, no raw rows read.
- No secrets, keys, account identifiers, raw market data, or absolute
  local paths are included here.

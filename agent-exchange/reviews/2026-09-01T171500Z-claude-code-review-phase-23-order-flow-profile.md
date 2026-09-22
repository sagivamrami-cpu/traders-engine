# Agent Exchange Review

Reviewer:
Claude Code

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-01T163500Z-claude-code-review-phase-23-order-flow-profile.md`

Created at:
2026-09-01T17:15:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT

Review of the Phase 23 GC order-flow ZIP profile (module, schema, metadata
and quality-gates configs, CLI, validator, tests, decision records).
Review-only; no implementation files were modified, no Databento API was
called, and no raw market-data rows were read. This review does not approve
feature construction, dataset construction, training, model promotion, live
trading, broker execution, or capital allocation.

## Contract confirmations (all eight)

1. Profile-only: CONFIRMED. The module reads ZIP structure, Parquet schema
   metadata, per-file row counts from Parquet metadata, and only the
   timestamp column of sampled files; nothing is extracted, resampled, or
   persisted. All approval booleans are schema consts `false`,
   `allowed_next_actions` has `maxItems: 0`.
2. `ORDER_FLOW_SOURCE_DECISION` stays open: CONFIRMED at three layers — the
   payload consts `order_flow_source_decision_status: OPEN_HUMAN_DECISION`;
   the builder emits a blocked reason if the decisions YAML carries ANY
   order-flow entry (even a non-approving one — correctly strict for a
   profile phase); and the validator asserts readiness keeps both items
   open (`satisfied_count=5`, `open_count=2`, `BLOCKED` — re-verified).
3. Options deferred and never queried: CONFIRMED. The YAML now records
   `OPTIONS_SOURCE_DECISION: DEFERRED` with an evidence record, the payload
   consts `DEFERRED_TO_V2_DO_NOT_QUERY`, and no options surface is touched.
4. No raw data/paths/secrets: CONFIRMED. Path redaction is tested at module
   and CLI level, the validator asserts no metadata/gates/decisions/zip
   path or `C:\`/`/Users/` appears in CLI output, the CLI has the sanitized
   error path (exit 1, fixed JSON), and the metadata config carries no
   `local_path` (tested).
5. 4H CSV and HHLL reference-only: CONFIRMED. `INGEST_ORDERFLOW_4H_CSV`,
   `JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS`, and
   `USE_HHLL_AS_TRADE_CONTRACT_LABEL` are blocked in the gates config, the
   first two also in the payload's schema-checked `blocked_actions`.
6. 30m candidate-only: CONFIRMED. `timeframe.status:
   RESEARCH_PARAMETER_PENDING` with `first_baseline_candidate: 30m` and an
   explicit `blocked_until_decided` list (session calendar, bar boundary,
   timestamp role, missing-bar policy, roll policy) — exactly the dataset
   gates this reviewer and Groq required.
7. CVD/cumulative blocked: CONFIRMED. `BLOCKED_PENDING_PIT_ERA_GAP_POLICY`
   is a schema const and the gates name the blocked feature families.
8. Macro per-source leakage-gated: CONFIRMED
   (`REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE`, `JOIN_MACRO_FEATURES`
   blocked, plus `USE_REVISED_MACRO_SERIES` denied — a good addition
   covering the vintage-data risk).

The five human decision records referenced by the configs all exist under
`agent-exchange/decisions/`, and the 2017 damaged-window gate carries its
evidence reference — the machine-enforced exclusion this reviewer required
now exists as config + schema consts + tests.

## Findings (by severity — none block acceptance)

### L1 — LOW: timestamp-column heuristic is invisible in the payload

`_parquet_profile` uses column `minute` when present, else the last column.
The fallback is safe (non-datetime columns yield `UNKNOWN`/null range), but
which column was profiled is not recorded. Recommend adding
`timestamp_column_by_file` to the payload in a later revision so a
misnamed vendor column is visible rather than silently unprofiled.

### L2 — LOW: naive timestamps are assumed UTC wall-clock for range strings

The `NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE` status labels the assumption
honestly, but the assumption itself is unverified. Before the Phase 24
dataset contract consumes these files, the vendor README/statement should
confirm the wall-clock timezone — fold this into the existing
`blocked_until_decided.TIMESTAMP_ROLE` gate.

### L3 — LOW: `_metadata_reasons` collapses all mismatches to one reason

Cosmetic: several wrong metadata fields report a single
`INVALID_ORDER_FLOW_METADATA`. Fine for fail-closed behavior; per-field
reasons would speed operator debugging.

## Commands run and results

- `python -m pytest tests/research/test_databento_gc_order_flow_profile.py tests/research/test_phase23_validator.py -q`:
  PASS, 6 passed.
- `python tools/validate_phase23.py`: PASS, `Phase 23 artifacts validated`
  (includes Phase 21 regression, schema check, readiness open-items check,
  and a temp-ZIP CLI redaction check).
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  `satisfied_count=5`, `open_count=2`, status `BLOCKED`, with
  `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` open.

## Blocking-issue statement

No blocking issues. All eight contracts hold, both prior reviews'
requirements are visibly encoded, and verification is green. Verdict:
ACCEPT. Recommended next step matches Codex's: Phase 24 should define the
GC dataset contract (resolving the five `blocked_until_decided` gates and
L2) before any feature construction.

Notes:
- Review-only: no files modified, no API calls, no raw rows read.
- No secrets, keys, account identifiers, raw market data, or absolute local
  paths are included here.

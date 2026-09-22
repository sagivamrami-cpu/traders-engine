# Phase 20 Databento GC ZIP Source Profile Report

## Scope

Phase 20 adds a read-only source-profile gate for the purchased Databento GC
one-second ZIP archive. The profiler reads parquet metadata and bounded
samples, validates structure (columns, UTC `ts_event` index, monotonicity,
duplicates, nulls, OHLC relationships, volume sign), checks the five approved
human decisions, and emits a sanitized JSON profile. It writes no raw
extracts, resamples nothing persistently, builds no candidate rows, trains
nothing, and approves nothing:
`production_allowed`, `dataset_construction_allowed`, and `training_allowed`
are all schema consts `false`, and `allowed_next_actions` is always empty.

## Source facts

From Codex's local inspection of the real archive (recorded in the GC
data-source plan; this session did not access the archive):

- 195 monthly Parquet entries, ~104,212,803 rows.
- Date range 2010-06-07T00:00:02Z through 2026-08-05T23:59:49Z.
- Columns `gc_open`, `gc_high`, `gc_low`, `gc_close`, `gc_volume`; UTC
  `ts_event` index; zero integrity failures.
- Three monthly samples resampled to 4H matched the derived `hhll_4h_L8R8_all`
  data exactly.

## Why GC, not XAUUSD

The archive is CME/COMEX gold futures data. Spot gold (`XAUUSD`) is a
different instrument with different sessions, funding, and microstructure.
The canonical symbol is a schema const `GC`; any GC-to-XAUUSD proxy use
requires a separate, explicitly approved proxy study and is out of scope.

## Recommendations carried in the profile contract

- `recommended_timeframe` const `4h`: matches the existing derived HHLL
  files and minimizes label-alignment risk.
- `day_session_policy_status` const `RESEARCH_DECISION_PENDING_MEASURE_FIRST`:
  the gold day/session definition must be measured, not hard-coded, before
  dataset construction (see also review gates G1/G3 in
  `agent-exchange/reviews/2026-08-31T220500Z-claude-code-review-gc-data-source-vendor-plan.md`).
- `hhll_label_role` const `AUXILIARY_DIRECTION_LABEL_ONLY`: HHLL LONG/SHORT
  is a direction label, not a trade-outcome label and not proof of edge.

## Files

- `trading_system/research/databento_gc_source_profile.py` (new): read-only
  ZIP profiler gated on the five approved GC decisions.
- `schemas/databento_gc_source_profile.schema.json` (new): sanitized profile
  contract; ready status requires exact GC columns, UTC `ts_event`, empty
  blocked reasons.
- `tools/inspect_databento_gc_zip.py` (new): CLI printing sorted sanitized
  JSON; sanitized error JSON on stderr.
- `tools/validate_phase20.py` (new): Phase 19 regression, profile tests,
  schema check, readiness check (5 satisfied / 2 open / BLOCKED), and a
  deterministic CLI run against a validator-generated test ZIP.
- `tests/research/test_databento_gc_source_profile.py` (new): 7 tests for
  the ready path, structural fail-closed paths, decision gating, and CLI
  redaction — all against synthetic test ZIPs, never the real archive.
- `tests/research/test_phase20_validator.py` (new): validator smoke test.
- Task 1 artifacts (requirements, symbol map, source inventory, GC metadata,
  decision records) were already present from Codex's routing pass and were
  verified, not modified.

## Verification

- `python -m pytest tests/research/test_databento_gc_source_profile.py tests/research/test_phase20_validator.py -v`: 8 passed.
- `python tools/validate_phase20.py`: `Phase 20 artifacts validated`.
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  `satisfied_count=5`, `open_count=2`, status `BLOCKED`.
- Full sweep and validators 0-20: see the Phase 20 status result in
  `agent-exchange/status/`.

## Groq-review hardening (post-implementation revision)

Incorporated from
`agent-exchange/reviews/2026-08-31T220800Z-groq-review-phase-20-databento-gc-source-profile.md`:

- F1: the profile now embeds a nested `source_identity` payload (from
  `validate_source_identity`), schema-locked to
  `REAL_SOURCE_PENDING_HUMAN_DECISION` or `BLOCKED` with
  `production_allowed` const false; fixture identity is remapped to
  `BLOCKED` with `FIXTURE_SOURCE_NOT_ALLOWED`. The sampled status was
  renamed to `PROFILE_SAMPLED_DATASET_BLOCKED` so it cannot read as a
  dataset/dry-run gate.
- F2: `blocked_actions` (schema-enforced) now also contains
  `RUN_OFFLINE_DRY_RUN`, `RESAMPLE_PERSISTENT_DATASET`, `COPY_RAW_SOURCE`,
  `MUTATE_RAW_SOURCE`, `UPLOAD_RAW_SOURCE`, and
  `INGEST_HHLL_DERIVED_LABELS` (14 denials total).
- F3/F4: new schema consts `contract_identity_status:
  UNDECLARED_PENDING_RESEARCH`, `roll_policy_status:
  RESEARCH_DECISION_PENDING`, and `ts_event_role:
  INTERVAL_START_NOT_BAR_CLOSE`; tests assert `XAUUSD` never appears in the
  payload; no session-calendar lookup is performed.
- F5: HHLL files are never read; `INGEST_HHLL_DERIVED_LABELS` is a blocked
  action and `hhll_label_role` stays `AUXILIARY_DIRECTION_LABEL_ONLY`.
- F6: new const `full_archive_quality_status: NOT_PROVEN_IN_PHASE_20` — the
  sampled status certifies sampled structure only, never the full archive.
- F7: a test pins the `databento-gc-1s` inventory entry to
  `OPEN_HUMAN_DECISION`.

## Deviations from the plan

- The validator runs `tests/research/test_databento_gc_source_profile.py`
  only; including `test_phase20_validator.py` as the plan wrote would recurse
  (the validator test invokes the validator). This matches the Phase 18/19
  validator pattern.
- Task 3 Step 4 (running the CLI against the real local archive) requires
  the ZIP path, which is supplied outside the repository and was not
  available to this session. The exact command for the human or Codex to run
  is in the status result; expected output is
  `PROFILE_SAMPLED_DATASET_BLOCKED` with `parquet_entry_count=195` and
  `row_count≈104212803`.

## Unresolved risks

- Bar-timestamp/`available_at` semantics, contract-roll policy, session
  calendar, and the vendor Parquet schema contract remain blocking gates for
  the dataset phase (review gates G1-G4).
- `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` remain open.
- The real-archive CLI smoke check has not run in this session.

## Next phase

Phase 21 (Databento GC 4H derived-bar adapter) after Groq review and Codex
acceptance, carrying gates G1-G4 as explicit requirements. Dataset
construction and training remain blocked until then and until the dataset
gate exists.

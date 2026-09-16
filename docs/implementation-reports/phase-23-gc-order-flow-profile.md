# Phase 23 GC Order Flow Profile Implementation Report

## Summary

Implemented a read-only GC order-flow archive profile gate. Phase 23 profiles the supplied local Databento GC order-flow archive shape, records sanitized metadata, records the timestamp column used for each sampled Parquet file, and keeps all feature-build, dataset, training, and trading actions blocked.

This phase does not approve `ORDER_FLOW_SOURCE_DECISION`, does not construct features, does not resample bars, does not train a model, does not call Databento APIs, and does not copy or extract raw market data.

## Files

- `docs/superpowers/plans/2026-09-01-phase-23-gc-order-flow-profile.md`
- `configs/data/databento-gc-order-flow-source-metadata.yaml`
- `configs/data/gc-order-flow-quality-gates.yaml`
- `schemas/databento_gc_order_flow_profile.schema.json`
- `trading_system/research/databento_gc_order_flow_profile.py`
- `tools/inspect_databento_gc_order_flow_zip.py`
- `tools/validate_phase23.py`
- `tests/research/test_databento_gc_order_flow_profile.py`
- `tests/research/test_phase23_validator.py`
- `agent-exchange/status/2026-09-01T161500Z-codex-gc-order-flow-review-intake.md`

## Real Archive Smoke Check

Sanitized profile of the supplied local archive returned:

- status: `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED`
- parquet files: `5`
- raw DBN.ZST tick files: `22`
- README present: `true`
- one-minute order-flow files: `GC_of_1m`, `GCall_of_1m`, `GCext_of_1m`
- one-minute OHLCV files: `GC_ohlcv_1m_fromticks`, `GCall_ohlcv_1m`
- order-flow ranges observed:
  - long series starts `2011-01-02T23:00:00Z`
  - tick-era series starts `2020-01-01T23:00:00Z`
  - extended aggregate ends `2026-07-17T20:59:00Z`
- timezone status:
  - `GC_of_1m` and `GC_ohlcv_1m_fromticks`: `UTC`
  - `GCall_*` and `GCext_*`: `NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE`
- timestamp column profiling:
  - sampled Parquet files now emit `timestamp_column_by_file`
  - observed sampled GC order-flow/OHLCV Parquet files use `minute`

The smoke output contained no local absolute archive path and no raw market-data rows.

## Gates Preserved

- `ORDER_FLOW_SOURCE_DECISION` remains `OPEN_HUMAN_DECISION`.
- `contract_identity_status` remains `UNDECLARED_PENDING_HUMAN_DECISION`.
- `OPTIONS_SOURCE_DECISION` is `DEFERRED` but still open in readiness.
- `gold_orderflow_4h.csv` remains `REFERENCE_ONLY_DO_NOT_INGEST`.
- 2017-01-01 through 2017-05-31 is recorded as a known damaged-aggressor interval, not the complete order-flow era policy.
- Archived `cvd` columns are marked precomputed/unsafe and `USE_ARCHIVED_CVD_COLUMN` / `INGEST_PRECOMPUTED_CVD` are blocked.
- CVD/cumulative features remain blocked pending a PIT, fold-local, era-gapped policy.
- 30m is now `first_baseline_candidate=30m_UTC_FIXED_BASELINE_APPROVED_V1`; this is a D1 v1 baseline approval, not a frozen model architecture or dataset-construction authorization.
- Macro features require per-source decisions and leakage gates before any dataset join.
- `MAP_GC_TO_XAUUSD` and `MAP_GC_TO_GLD` are explicitly blocked.

## Verification

- `python -m pytest tests\research\test_databento_gc_order_flow_profile.py -q`: PASS, 5 passed.
- `python tools\validate_phase23.py`: PASS, `Phase 23 artifacts validated`.
- Real local archive smoke check: PASS, status `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED`.
- `python tools\real_data_readiness.py --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml`: PASS, status `BLOCKED`, `satisfied_count=5`, `open_count=2`.
- `python tools\validate_phase20.py`: PASS.
- `python tools\validate_phase21.py`: PASS.

## Review Inputs Addressed

- Claude Code Phase 23 L1: added `timestamp_column_by_file` to the profile payload and schema so Phase 24 can see which timestamp column was used.
- Groq F1: narrowed order-flow to profile-only; no readiness source approval.
- Groq F2: treated 2017 window as known damage only, not complete era policy.
- Groq F3: kept 30m as a non-final baseline; later D1 intake updated the value to the approved v1 baseline while leaving dataset construction blocked.
- Groq F4: blocked CVD and cumulative order-flow features until PIT/era policy exists.
- Groq F5: added explicit archived/precomputed CVD denials and status fields.
- Groq F6: blocked 4H CSV, HHLL, options query, revised macro series, and GC alias mapping in training rows and labels.
- Groq F7: added schema validation inside `to_payload()`.
- Groq F7: narrowed macro to per-source leakage-gated.
- Claude C2/C3/C4/C5/C6: implemented machine-readable gates, reference-only enforcement, timeframe candidate status, macro narrowing, and validator coverage.

## Unresolved Risks

- The local order-flow archive's contract identity is still not declared as dated, parent, or continuous.
- The full availability-era policy is not complete; Phase 23 only profiles and records known issues.
- 30m resampling still requires session calendar, missing-bar, roll/identity, and dataset-construction gates.
- Macro feature sources still require separate source decisions and point-in-time availability policies.
- Order-flow source approval for feature construction remains intentionally unapproved.

## Next Phase

Phase 24 should define the GC dataset contract before any feature build:

- canonical input files
- timezone normalization
- order-flow era policy
- CVD/cumulative-feature policy
- 4H/HHLL exclusion rules
- 30m resample recipe, if retained
- leakage gates for labels and macro features

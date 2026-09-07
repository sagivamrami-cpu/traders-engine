# Phase 30 GC Timestamp Evidence Implementation Report

## Summary

Implemented a sanitized GC timestamp-evidence report. The report reads only ZIP member names, Parquet schema metadata, timestamp-column types, row counts, and README evidence flags. It does not emit prices, volumes, deltas, trades, raw rows, local absolute paths, secrets, or vendor payloads.

This phase collected evidence only. The later D3 decision record approved the v1 timestamp interpretation, but still does not allow resampling, order-flow/OHLCV joins, label building, dataset construction, or training.

## Files

- `schemas/gc_timestamp_evidence_report.schema.json`
- `trading_system/research/gc_timestamp_evidence.py`
- `tools/inspect_gc_timestamp_evidence.py`
- `tools/validate_phase30.py`
- `tests/research/test_gc_timestamp_evidence.py`
- `tests/research/test_phase30_validator.py`

## Real Local Evidence Observed

Sanitized command:

`python tools\inspect_gc_timestamp_evidence.py --ohlcv-zip <LOCAL_GC_1S_ZIP> --order-flow-zip <LOCAL_GC_ORDER_FLOW_ZIP>`

Observed from local metadata:

- Historical OHLCV 1s source:
  - inspected member: `gc_1s/gc_1s_2010-06.parquet`
  - timestamp column: `ts_event`
  - timestamp type: `timestamp[ns, tz=UTC]`
  - timezone status: `UTC_AWARE`
  - role evidence status: `COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN`
- Order-flow 1m source:
  - inspected member: `gc/GCext_of_1m.parquet`
  - timestamp column: `minute`
  - timestamp type: `timestamp[ns]`
  - timezone status: `TIMEZONE_NAIVE_UTC_WALL_CLOCK_CLAIM_REQUIRES_DECISION`
  - role evidence status: `ONE_MINUTE_AGGREGATE_COLUMN_SCHEMA_ONLY_START_OR_END_NOT_PROVEN`
- Order-flow README evidence:
  - README present: true
  - naive UTC wall-clock claim present: true
  - damaged 2017 warning present: true

## Required Human Decisions

- Resolved by `agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md`.

## Blocked Actions

- `RESAMPLE_REAL_BARS`
- `JOIN_ORDER_FLOW_TO_OHLCV`
- `BUILD_REAL_DATASET`
- `BUILD_REAL_LABELS`
- `TRAIN_PRODUCTION_MODEL`

## Verification

- `python -m pytest tests\research\test_gc_timestamp_evidence.py -q`: PASS, 3 passed.
- `python -m pytest tests\research\test_phase30_validator.py -q`: PASS, 1 passed.
- `python tools\validate_phase30.py`: PASS, `Phase 30 artifacts validated`.

## Next

D3 is resolved for v1 timestamp interpretation. Continue to the next unsatisfied gate before any resampling, order-flow/OHLCV join, dataset construction, label building, or training.

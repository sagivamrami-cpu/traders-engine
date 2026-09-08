# Phase 13 Local CSV Inspection Report

## Scope

Phase 13 adds a local OHLCV CSV inspection tool that computes file hash, row
count, raw symbols, required-column status, observed UTC date range, and
suggested unapproved metadata for single-symbol files.

It does not write metadata files, copy raw CSV data, approve vendors, train a
model, backtest, integrate a broker, run live execution, deploy, or allocate
capital.

## Files

- schemas/local_csv_inspection_report.schema.json: inspection report contract
- trading_system/data_foundation/csv_inspection.py: inspection report builder
- tools/inspect_local_ohlcv_csv.py: CLI that prints inspection JSON
- tools/validate_phase13.py: deterministic Phase 13 validator
- tests/data_foundation/test_csv_inspection.py: inspection behavior tests
- tests/data_foundation/test_phase13_validator.py: validator smoke test

## Tests

- `python -m pytest tests/data_foundation/test_csv_inspection.py -v`
- `python -m pytest tests/data_foundation/test_phase13_validator.py -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`
- `python tools/validate_phase7.py`
- `python tools/validate_phase8.py`
- `python tools/validate_phase9.py`
- `python tools/validate_phase10.py`
- `python tools/validate_phase11.py`
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`

## Decisions

- Inspection output is JSON-only and does not write generated metadata files.
- Suggested metadata uses `OPEN_HUMAN_DECISION`.
- Multi-symbol CSV files are blocked until split into one symbol per file.
- The inspector uses Phase 1 timestamp policy for observed date ranges.
- Inspection does not require a symbol-map entry and does not imply source
  approval.

## Unresolved Risks

- No real historical CSV has been provided.
- No production OHLCV vendor or local-only source decision has been approved.
- No raw-data storage root, retention duration, or license has been approved.
- No order-flow or options source decision has been recorded.
- No real out-of-sample, shadow, or paper trading evidence exists.

## Next Phase

The next phase requires a real CSV from the user. The expected flow is inspect,
create human-reviewed metadata, validate source bundle, then run local dry-run.

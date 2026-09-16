# Phase 8 Local CSV Onboarding Report

## Scope

Phase 8 adds a local OHLCV CSV onboarding path that validates file shape,
normalizes timestamps and symbols through Phase 1 policies, computes a raw-file
hash, and emits a RawSourceManifest-compatible payload.

It does not approve any production vendor, fetch network data, train a model,
backtest, integrate a broker, run live execution, or allocate capital.

## Files

- configs/data/local-csv-onboarding-template.yaml: fixture-safe metadata template
- trading_system/data_foundation/csv_onboarding.py: CSV validation and manifest builder
- tools/onboard_ohlcv_csv.py: CLI that prints RawSourceManifest JSON
- tools/validate_phase8.py: deterministic Phase 8 validator
- tests/data_foundation/test_csv_onboarding.py: onboarding behavior tests
- tests/data_foundation/test_phase8_validator.py: validator smoke test

## Tests

- `python -m pytest tests/data_foundation/test_csv_onboarding.py -v`
- `python -m pytest tests/data_foundation/test_phase8_validator.py -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`
- `python tools/validate_phase7.py`
- `python tools/validate_phase8.py`

## Decisions

- Local CSV sources default to `OPEN_HUMAN_DECISION`.
- The raw CSV remains an immutable input and is not copied or rewritten.
- Required OHLCV columns are enforced before normalization.
- Unknown symbols fail through the existing Phase 1 symbol map.
- Observed date ranges are derived from normalized UTC timestamps.

## Unresolved Risks

- No production data vendor has been approved.
- No production storage policy exists for user-provided raw CSV files.
- No multi-symbol or multi-timeframe onboarding policy exists.
- No real out-of-sample training evidence exists.

## Next Phase

The next phase should define production data-source selection and raw-data
storage policy, or remain limited to validation-only tooling until those human
decisions are available.

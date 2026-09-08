# Phase 11 Local Source Bundle Validation Report

## Scope

Phase 11 adds a single validation entrypoint for a local CSV source bundle:
CSV file, metadata YAML, and raw-data retention policy. It runs CSV onboarding,
retention evaluation, and the offline research dry-run, then reports whether the
bundle is accepted for local dry-run use.

It does not approve production data, copy raw CSV files, retain raw data,
promote models, backtest, integrate a broker, run live execution, deploy, or
allocate capital.

## Files

- schemas/source_bundle_validation.schema.json: bundle validation contract
- trading_system/research/source_bundle.py: bundle validation orchestrator
- tools/validate_local_source_bundle.py: CLI that prints bundle validation JSON
- tools/validate_phase11.py: deterministic Phase 11 validator
- tests/research/test_source_bundle.py: bundle validation behavior tests
- tests/research/test_phase11_validator.py: validator smoke test

## Tests

- `python -m pytest tests/research/test_source_bundle.py -v`
- `python -m pytest tests/research/test_phase11_validator.py -v`
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

## Decisions

- Bundle validation accepts local inputs for dry-run only.
- Retention policy must pass before a dry-run summary is produced.
- `ACCEPTED_FOR_DRY_RUN` is not production source approval.
- Raw retention and model promotion remain blocked in the validation payload.
- Non-open local metadata status blocks the bundle.

## Unresolved Risks

- No real historical CSV has been provided.
- No production data vendor has been approved.
- No raw-data storage root, retention duration, or license has been approved.
- Candidate rules, labels, costs, fills, and splits remain fixture policies.
- No real out-of-sample, shadow, or paper trading evidence exists.

## Next Phase

The next phase should add a real-data readiness checklist that tells a human
exactly which fields, files, and approvals are missing before the first
production-grade training dataset can be built.

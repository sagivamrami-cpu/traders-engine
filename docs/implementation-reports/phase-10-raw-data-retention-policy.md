# Phase 10 Raw Data Retention Policy Report

## Scope

Phase 10 adds a raw-data retention and license policy for user-provided local
CSV inputs. It allows manifest and dry-run outputs while blocking raw CSV copy,
mutation, network upload, vendor approval, and model promotion.

It does not store raw CSV files, approve a production data vendor, fetch network
data, train a model, backtest, integrate a broker, run live execution, deploy,
or allocate capital.

## Files

- schemas/raw_data_retention_policy.schema.json: retention policy contract
- configs/data/raw-data-retention-policy.yaml: manifest-only local CSV policy
- trading_system/data_foundation/storage_policy.py: policy loader and evaluator
- tools/validate_phase10.py: deterministic Phase 10 validator
- tests/data_foundation/test_storage_policy.py: policy behavior tests
- tests/data_foundation/test_phase10_validator.py: validator smoke test

## Tests

- `python -m pytest tests/data_foundation/test_storage_policy.py -v`
- `python -m pytest tests/data_foundation/test_phase10_validator.py -v`
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

## Decisions

- Raw retention remains unapproved until an explicit human decision exists.
- Local CSV source status must remain `OPEN_HUMAN_DECISION`.
- Manifest and dry-run outputs are allowed without copying raw CSV files.
- Raw copy, mutation, and network upload are hard-blocked by default policy.
- Approved storage roots remain empty until the storage policy is changed by a
  human-owned decision.

## Unresolved Risks

- No production data vendor has been approved.
- No real historical CSV has been provided.
- No raw-data storage root, retention duration, or license has been approved.
- No real out-of-sample, shadow, or paper trading evidence exists.

## Next Phase

The next phase can safely add a local source bundle validator that checks a
real CSV plus metadata plus retention policy together before any dry-run is
accepted as a reproducible research input.

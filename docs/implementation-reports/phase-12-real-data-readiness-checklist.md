# Phase 12 Real Data Readiness Checklist Report

## Scope

Phase 12 adds a machine-readable readiness checklist showing which real-data
inputs and approvals are missing before production-grade dataset construction
or model training. The default report is blocked because the repo currently has
fixture/synthetic evidence only.

It does not approve a vendor, fetch data, store raw data, train a model,
backtest, integrate a broker, run live execution, deploy, or allocate capital.

## Files

- schemas/real_data_readiness_report.schema.json: readiness report contract
- configs/research/real-data-readiness-checklist.yaml: required human inputs
- trading_system/research/readiness.py: checklist loader and report builder
- tools/real_data_readiness.py: CLI that prints readiness JSON
- tools/validate_phase12.py: deterministic Phase 12 validator
- tests/research/test_real_data_readiness.py: readiness behavior tests
- tests/research/test_phase12_validator.py: validator smoke test

## Tests

- `python -m pytest tests/research/test_real_data_readiness.py -v`
- `python -m pytest tests/research/test_phase12_validator.py -v`
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

## Decisions

- No readiness item is satisfied by default.
- Fixture and synthetic data do not satisfy real-data readiness.
- Production dataset construction and model training remain blocked.
- Order-flow and options sources require approval or explicit defer decisions.
- Storage and license approval remain separate from local dry-run validation.

## Unresolved Risks

- No real historical CSV has been provided.
- No production OHLCV vendor or local-only source decision has been approved.
- No raw-data storage root, retention duration, or license has been approved.
- No order-flow or options source decision has been recorded.
- No real out-of-sample, shadow, or paper trading evidence exists.

## Next Phase

The next phase requires user-provided real-data input or explicit human
decisions. Until then, implementation should stop at blocked readiness and avoid
inventing production evidence.

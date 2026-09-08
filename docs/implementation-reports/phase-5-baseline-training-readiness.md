# Phase 5 Baseline Training Readiness Report

## Scope

Phase 5 adds a research-only training readiness gate and deterministic
majority-class baseline harness.

It does not implement live model serving, prediction APIs, backtesting, broker
integration, capital allocation, or production promotion.

## Files

- schemas/model_training_run.schema.json: training run manifest contract
- configs/models/baseline-training-policy.yaml: research-only readiness policy
- trading_system/models: training manifest, readiness checks, and majority baseline
- tests/models: contract, readiness, baseline, and validator tests
- tools/validate_phase5.py: deterministic Phase 5 validator

## Tests

- `python -m pytest tests/models -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`

## Decisions

- Fixture-sized datasets are blocked from training.
- Only included training rows participate in readiness and baseline fitting.
- Rejected, ambiguous, and excluded rows are ignored for fitting.
- Chronological splits are consumed as provided; no random split exists.
- Phase 5 can train only a majority-class research baseline.
- `promotion_allowed` is always false.

## Unresolved Risks

- No real data source is approved.
- No real dataset with enough included rows exists.
- No calibrated model exists.
- No walk-forward evaluator exists.
- No production promotion package exists.

## Next Phase

Phase 6 should add walk-forward evaluation and calibration reports for a real
vertical-slice dataset. That phase requires approved production data inputs and
enough included candidate rows across at least two outcome classes.

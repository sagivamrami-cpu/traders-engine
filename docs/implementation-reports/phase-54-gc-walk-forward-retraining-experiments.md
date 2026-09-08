# Phase 54: GC Walk-Forward Retraining Experiments

## Purpose

Phase 54 converts the Phase 53 stability review into a bounded experiment plan for chronological retraining.

This phase does not train the next model yet. It defines which walk-forward retraining experiments should be run, why they matter, and what gates must remain closed before any promotion discussion.

## Why This Is Needed

Phase 53 showed that the normalized model is better than the first real model, but not stable enough:

- Overall TEST expected R per candidate: `0.00038432494158456814`
- LONG expected R per candidate: `0.01354722019934434`
- SHORT expected R per candidate: `-0.012778570316175205`
- LOW-volatility expected R per candidate: `-0.0020082638580663616`
- MID-volatility expected R per candidate: `0.0008112487018551749`
- HIGH-volatility expected R per candidate: `0.0008284562660481121`
- Higher threshold `0.55` expected R per candidate: `-0.0005158404625912664`
- Negative TEST months: `13` of `31`

Interpretation for trading:

The model has a weak positive average, but the source of the result is uneven. LONG candidates look much stronger than SHORT candidates, and LOW volatility weakens the model. A static model trained once is not enough evidence.

## Experiment Matrix

The report prioritizes six bounded experiments:

1. `LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`
2. `LONG_ONLY_WALK_FORWARD_RETRAINING`
3. `MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`
4. `ALL_CANDIDATES_WALK_FORWARD_COMPARATOR`
5. `SHORT_ONLY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`
6. `LOW_VOLATILITY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`

The first experiment is the main candidate because it combines the two strongest Phase 53 findings: LONG direction and MID/HIGH volatility.

## Compute Boundary

The next execution phase is intentionally bounded:

- Maximum windows: `8`
- Window stride: every `3` months
- Validation window: `3` months
- Epochs per window: `80`
- Minimum train rows per window: `50000`
- Minimum validation rows per window: `5000`
- Minimum test rows per window: `1000`
- Threshold grid: `0.45`, `0.475`, `0.5`, `0.525`, `0.55`

This keeps the next retraining run useful without turning it into an open-ended compute job.

## Decision Rules

- Promotion remains forbidden until a later human-approved promotion phase.
- A primary experiment must beat the all-candidate walk-forward comparator on median expected R per candidate.
- A primary experiment must have positive expected R per candidate in at least six evaluated windows.
- No TEST window may be used for threshold selection of the same window.
- SHORT and LOW-volatility diagnostic experiments cannot become promoted variants directly.

## Promotion Boundary

Promotion remains blocked:

- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_walk_forward_experiments_report.schema.json`
- Module: `trading_system/models/gc_walk_forward_experiments.py`
- CLI: `tools/gc_walk_forward_experiments.py`
- Validator: `tools/validate_phase54.py`
- Report: `configs/models/gc-walk-forward-experiments-report.json`
- Tests:
  - `tests/models/test_gc_walk_forward_experiments.py`
  - `tests/models/test_gc_walk_forward_experiments_cli.py`
  - `tests/research/test_phase54_validator.py`

## Verification

```powershell
python -m pytest tests\models\test_gc_walk_forward_experiments.py tests\models\test_gc_walk_forward_experiments_cli.py tests\research\test_phase54_validator.py -q
python tools\validate_phase54.py
python -m py_compile trading_system\models\gc_walk_forward_experiments.py tools\gc_walk_forward_experiments.py tools\validate_phase54.py
```

Result:

- 4 tests passed.
- Phase 54 validator passed.
- Python compile check passed.
- Local path / secret scan found no matches.

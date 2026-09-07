# Phase 55: Execute Bounded Walk-Forward Retraining

## Purpose

Phase 55 executes the bounded walk-forward retraining experiments defined in Phase 54.

This is still research-only. It trains temporary per-window models to test stability, but it does not export a promoted trading model.

## Method

For each selected TEST month:

1. Train rows are all eligible rows before the validation window.
2. Validation rows are the three months before the TEST month.
3. TEST rows are one forward month.
4. Feature normalization is fitted on that window's train rows only.
5. Threshold is selected on validation only from: `0.45`, `0.475`, `0.5`, `0.525`, `0.55`.
6. TEST is scored only after training and threshold selection are complete.

The run used the Phase 54 compute budget:

- Maximum windows: `8`
- Window stride: every `3` months
- Validation months: `3`
- Epochs per window: `80`
- Minimum train rows per window: `50000`
- Minimum validation rows per window: `5000`
- Minimum test rows per window: `1000`

## Results

Best primary experiment:

- `MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`
- Valid windows: `1`
- Positive TEST windows: `1`
- Median TEST expected R per candidate: `0.001314060446780552`
- Delta versus comparator median: `0.002649902300038213`
- Pass gate: `false`

Comparator:

- `ALL_CANDIDATES_WALK_FORWARD_COMPARATOR`
- Valid windows: `8`
- Positive TEST windows: `3`
- Median TEST expected R per candidate: `-0.001335841853257661`
- Mean TEST expected R per candidate: `-0.0007133044924106577`
- Minimum TEST expected R per candidate: `-0.004207376262930845`

Skipped filtered experiments:

- `LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`: `0` valid windows, `8` skipped
- `LONG_ONLY_WALK_FORWARD_RETRAINING`: `0` valid windows, `8` skipped
- `SHORT_ONLY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`: `0` valid windows, `8` skipped
- `LOW_VOLATILITY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`: `0` valid windows, `8` skipped

## Trading Interpretation

The all-candidate walk-forward comparator is negative across the bounded experiment. That means the static positive result from Phase 52/53 does not hold strongly enough when retraining chronologically.

The MID/HIGH-volatility variant had one positive valid window, but one window is not enough. The LONG-filtered variants did not have enough validation/test rows under the current strict row thresholds.

## Conclusion

The experiment does not support model promotion.

The next phase should review the walk-forward results and decide whether to:

- lower minimum row thresholds for filtered variants,
- use longer validation/test windows,
- run direction-specific experiments separately,
- revise the volatility bucketing policy,
- or stop this model family and return to feature/label design.

## Promotion Boundary

Promotion remains blocked:

- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_bounded_walk_forward_retraining_run.schema.json`
- Module: `trading_system/models/gc_bounded_walk_forward_retraining.py`
- CLI: `tools/run_gc_bounded_walk_forward_retraining.py`
- Validator: `tools/validate_phase55.py`
- Run: `configs/models/gc-bounded-walk-forward-retraining-run.json`
- Tests:
  - `tests/models/test_gc_bounded_walk_forward_retraining.py`
  - `tests/models/test_gc_bounded_walk_forward_retraining_cli.py`
  - `tests/research/test_phase55_validator.py`

## Verification

```powershell
python -m pytest tests\models\test_gc_bounded_walk_forward_retraining.py tests\models\test_gc_bounded_walk_forward_retraining_cli.py tests\research\test_phase55_validator.py -q
python tools\validate_phase55.py
python -m py_compile trading_system\models\gc_bounded_walk_forward_retraining.py tools\run_gc_bounded_walk_forward_retraining.py tools\validate_phase55.py
```

Result:

- 4 tests passed.
- Phase 55 validator passed.
- Python compile check passed.
- Local path / secret scan found no matches.

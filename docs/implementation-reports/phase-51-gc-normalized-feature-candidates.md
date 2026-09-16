# Phase 51: GC Normalized Feature Candidates

## Purpose

Phase 50 showed that the first real GC model did not confirm on TEST and that several raw inputs drifted between TRAIN and TEST. Phase 51 turns that diagnosis into a controlled feature plan for the next research model.

This phase does not train a model. It defines what the next model is allowed to train on.

## Input

- Source diagnostics: `configs/models/gc-feature-diagnostics-report.json`
- Dataset id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- Variant: `order_flow`
- Rows by split:
  - TRAIN: 238398
  - VALIDATION: 45074
  - TEST: 57584

## Key Decision

Raw `close` and raw `atr_14` are excluded from the next model feature set.

Reason:
- `close` had the largest TRAIN-to-TEST drift in Phase 50.
- `atr_14` also drifted materially.
- Using these raw fields can teach the model the historical price/volatility era instead of the trade setup behavior.

## Next Research Feature Set

Approved existing features:
- `ret_1`
- `ret_4`
- `ret_8`
- `ret_14`
- `range_over_atr`
- `direction_is_long`
- `direction_is_short`

New normalized candidates:
- `atr_14_over_close`
- `of_delta_over_of_volume`
- `of_delta_sum_14_over_of_volume_sum_14`
- `of_trades_per_minute`
- `of_volume_per_trade`
- `of_volume_vs_14bar_avg`
- `of_trades_vs_14bar_avg`

## Leakage Guard

The next model feature set must not include:
- `outcome_class`
- `net_return_r`
- `time_to_outcome_bars`
- `entry_price`
- `target_price`
- `stop_price`
- `risk_r`

These fields are labels, outcomes, or trade-contract values. They can be used for evaluation and reporting, but not as model inputs.

## Training Boundary

Research training is allowed for the next phase:

- Next phase: `PHASE_52_NORMALIZED_FEATURE_MODEL_RETRAINING`
- Training controls:
  - `TRAIN_ONLY_IMPUTATION_AND_STANDARDIZATION`
  - `VALIDATION_ONLY_THRESHOLD_SELECTION`
  - `TEST_ONLY_FINAL_EVALUATION`
  - `NO_LABEL_OR_OUTCOME_FEATURE_INPUTS`

Promotion remains blocked:

- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_normalized_feature_candidates_report.schema.json`
- Module: `trading_system/models/gc_normalized_feature_candidates.py`
- CLI: `tools/gc_normalized_feature_candidates.py`
- Validator: `tools/validate_phase51.py`
- Report: `configs/models/gc-normalized-feature-candidates-report.json`
- Tests:
  - `tests/models/test_gc_normalized_feature_candidates.py`
  - `tests/models/test_gc_normalized_feature_candidates_cli.py`
  - `tests/research/test_phase51_validator.py`

## Verification

Focused verification:

```powershell
python -m pytest tests\models\test_gc_normalized_feature_candidates.py tests\models\test_gc_normalized_feature_candidates_cli.py tests\research\test_phase51_validator.py -q
```

Result:

```text
5 passed
```

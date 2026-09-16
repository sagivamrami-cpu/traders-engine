# Phase 52: GC Normalized Feature Model Retraining

## Purpose

Phase 52 trains a research-only GC model using the normalized feature set approved in Phase 51.

The goal is not to approve trading. The goal is to check whether removing raw drifted features and replacing them with normalized ratios improves out-of-sample behavior.

## Input

- Dataset: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- Variant: `order_flow`
- Rows by split:
  - TRAIN: 238398
  - VALIDATION: 45074
  - TEST: 57584
- Source feature plan: `configs/models/gc-normalized-feature-candidates-report.json`
- Previous model: `configs/models/gc-first-real-model-run.json`
- Baseline: `configs/models/gc-majority-baseline-training-run.json`

## Model

- Model type: `REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH`
- Solver: `in_repo_batch_gradient_descent`
- Epochs: 220
- Fit scope: `TRAIN_ONLY`
- Threshold selection: `VALIDATION_ONLY`
- Final evaluation: `TEST_ONLY`
- Selected threshold: `0.50`

## Features Used

The model used:

- `ret_1`
- `ret_4`
- `ret_8`
- `ret_14`
- `range_over_atr`
- `direction_is_long`
- `direction_is_short`
- `atr_14_over_close`
- `of_delta_over_of_volume`
- `of_delta_sum_14_over_of_volume_sum_14`
- `of_trades_per_minute`
- `of_volume_per_trade`
- `of_volume_vs_14bar_avg`
- `of_trades_vs_14bar_avg`

The model did not use raw `close` or raw `atr_14`.

## Results

Validation:

- Accuracy: `0.4241247725961752`
- Expected R per candidate: `0.0018140593341341342`
- Expected R per selected trade: `0.003399447487912608`
- Selected trade rate: `0.533633580334561`

Test:

- Accuracy: `0.4408342595165324`
- Expected R per candidate: `0.00038432494158456814`
- Expected R per selected trade: `0.0010412122999861571`
- Selected trade rate: `0.36911294804112255`

Comparison:

- Test accuracy vs previous model: `+0.0011287857738260798`
- Test expected R per candidate vs previous model: `+0.0011336117278897852`
- Test accuracy vs majority baseline: `+0.0003820505696026655`
- Validation expected R per candidate vs previous model: `-0.0006002137064462804`

## Interpretation

The normalized model improved TEST behavior relative to the first real model:

- TEST expected R per candidate moved from negative to slightly positive.
- TEST expected R per selected trade moved from negative to slightly positive.
- TEST accuracy improved slightly over both the first real model and the majority baseline.

The improvement is small and must not be treated as proven edge. The next work should stress-test stability across regimes, thresholds, and walk-forward windows before any promotion decision.

## Promotion Boundary

Promotion remains blocked:

- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_normalized_feature_model_run.schema.json`
- Module: `trading_system/models/gc_normalized_feature_model.py`
- CLI: `tools/train_gc_normalized_feature_model.py`
- Validator: `tools/validate_phase52.py`
- Run: `configs/models/gc-normalized-feature-model-run.json`
- Tests:
  - `tests/models/test_gc_normalized_feature_model.py`
  - `tests/models/test_train_gc_normalized_feature_model_cli.py`
  - `tests/research/test_phase52_validator.py`

## Verification

Focused verification:

```powershell
python -m pytest tests\models\test_gc_normalized_feature_model.py tests\models\test_train_gc_normalized_feature_model_cli.py tests\research\test_phase52_validator.py -q
python tools\validate_phase52.py
```

Result:

```text
7 passed
Phase 52 artifacts validated
```

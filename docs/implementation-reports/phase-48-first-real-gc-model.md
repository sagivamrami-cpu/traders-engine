# Phase 48 First Real GC Model

## Summary

Phase 48 trained the first real predictive GC 30m research model on the locked
Phase 46 `order_flow` dataset.

This is not a promotion candidate and not an edge claim. It is the first
non-majority predictive baseline that tests whether the current tree-derived
feature set contains signal beyond a trivial class baseline.

## Model

- model_type: `REGULARIZED_LOGISTIC_RESEARCH_BASELINE`
- model_version: `regularized-logistic-research-baseline-0.1.0`
- target class: `TARGET_FIRST`
- negative classes: `STOP_FIRST_OR_EXPIRED`
- solver: `in_repo_batch_gradient_descent`
- fit scope: `TRAIN_ONLY`
- threshold selection scope: `VALIDATION_ONLY`
- final evaluation scope: `TEST_ONLY`
- selected threshold: `0.5599999999999999`
- promotion_allowed: `false`

## Dataset

- dataset_id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- variant: `order_flow`
- train rows: `238398`
- validation rows: `45074`
- test rows: `57584`
- class distribution:
  - EXPIRED: `47922`
  - STOP_FIRST: `146567`
  - TARGET_FIRST: `146567`

## Feature Set

- `atr_14`
- `close`
- `of_delta`
- `of_delta_sum_14`
- `of_minutes_present`
- `of_trades`
- `of_trades_sum_14`
- `of_volume`
- `of_volume_sum_14`
- `range_over_atr`
- `ret_1`
- `ret_4`
- `ret_8`
- `ret_14`
- `seconds_with_trades`
- `volume_30m`
- `direction_is_long`
- `direction_is_short`

## Results

Majority baseline:

- validation_accuracy: `0.4223499134756179`
- test_accuracy: `0.4404522089469297`

First real model:

- validation_accuracy: `0.4247681590273772`
- test_accuracy: `0.4397054737427063`
- validation_expected_r_per_candidate: `0.0024142730405804147`
- test_expected_r_per_candidate: `-0.0007492867863052171`
- validation_expected_r_per_selected_trade: `0.01251103047035199`
- test_expected_r_per_selected_trade: `-0.00545887276095643`
- validation_selected_trade_rate: `0.19297155788259307`
- test_selected_trade_rate: `0.13726035009724924`

## Interpretation

The model shows a small positive validation signal but does not confirm on TEST.
It slightly improves validation accuracy versus the majority baseline, but test
accuracy is slightly lower than the majority baseline and expected R is negative
on TEST.

The correct conclusion is: the pipeline can now train a real model, but the
current feature/label configuration has not proven a tradable edge.

## Safety Boundary

- No model promotion was authorized.
- No live trading was authorized.
- No broker execution was authorized.
- No capital allocation was authorized.
- No vendor API was queried.
- No commit or push was performed.

## Artifacts

- `trading_system/models/first_real_gc_model.py`
- `tools/train_gc_first_real_model.py`
- `tools/validate_phase48.py`
- `schemas/gc_first_real_model_run.schema.json`
- `configs/models/gc-first-real-model-run.json`

## Verification

- `python -m pytest tests\models\test_first_real_gc_model.py tests\models\test_train_gc_first_real_model_cli.py -q`: PASS, `4 passed`.
- `python tools\validate_phase47.py`: PASS, `Phase 47 artifacts validated`.
- `python tools\train_gc_first_real_model.py --build-manifest configs\datasets\gc-30m-real-dataset-build-manifest.json --rows-root market-data\gc-30m-real --training-policy configs\models\baseline-training-policy.yaml --variant order_flow --run-out configs\models\gc-first-real-model-run.json`: PASS.
- `python -m pytest tests\research\test_phase48_validator.py -q`: PASS, `1 passed`.
- `python -m pytest tests\models\test_first_real_gc_model.py tests\models\test_train_gc_first_real_model_cli.py tests\research\test_phase48_validator.py -q`: PASS, `5 passed in 76.08s`.
- `python tools\validate_phase48.py`: PASS, `Phase 48 artifacts validated`.

## Review Fixes

- Expected-R metrics now use the dataset `net_return_r` carried into
  `CandidateTrainingRow.outcome_return_r`.
- The model blocks unapproved/leaky feature names before feature discovery.
- `validate_phase48.py` rejects unapproved run feature names and scans Phase 48
  run/report/exchange artifacts for common local absolute paths.

## Recommended Next Step

Ask Claude Code to review Phase 48 for leakage risk, split handling, threshold
selection, and metric interpretation. If accepted, Phase 49 should focus on
feature diagnostics and model experiment design rather than promotion.

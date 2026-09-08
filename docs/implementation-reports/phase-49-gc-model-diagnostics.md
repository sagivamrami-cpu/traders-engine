# Phase 49 GC Model Diagnostics

## Summary

Phase 49 adds a research-only diagnostics report for the Phase 48 first real GC
model. It compares the model to the Phase 47 majority baseline and records why
the current result must not be promoted.

## Inputs

- Baseline run: `configs/models/gc-majority-baseline-training-run.json`
- First real model run: `configs/models/gc-first-real-model-run.json`

## Diagnostics Result

- status: `FEATURE_DIAGNOSTICS_REQUIRED`
- promotion_allowed: `false`
- blocked_reasons:
  - `NEGATIVE_TEST_EXPECTED_R`
  - `TEST_ACCURACY_NOT_ABOVE_BASELINE`
- recommended_next_phase: `PHASE_50_FEATURE_DIAGNOSTICS_AND_EXPERIMENT_DESIGN`

## Metric Deltas

- validation_accuracy_delta_vs_baseline: `0.0024182455517592905`
- test_accuracy_delta_vs_baseline: `-0.0007467352042234143`
- validation_expected_r_per_candidate: `0.0024142730405804147`
- test_expected_r_per_candidate: `-0.0007492867863052171`
- validation_selected_trade_rate: `0.19297155788259307`
- test_selected_trade_rate: `0.13726035009724924`

## Top Coefficients

These are model coefficients, not causal feature importance and not trading
edge evidence.

- `of_trades_sum_14`: `-0.17050700379751957`
- `of_volume_sum_14`: `-0.13519846060421709`
- `seconds_with_trades`: `0.08507727131343076`
- `range_over_atr`: `0.03418078000633729`
- `atr_14`: `-0.032253432396695716`
- `of_volume`: `0.02766297568813643`
- `volume_30m`: `0.02766297568813643`
- `of_trades`: `0.02467118501226514`
- `ret_14`: `-0.013704475334619496`
- `close`: `0.013453321705632178`

## Interpretation

The model has a small validation improvement, but TEST does not confirm it.
Phase 49 therefore blocks promotion and routes the project to feature
diagnostics and experiment design.

For a trader, this means the current tree-derived feature set is trainable, but
the first model does not yet show evidence that it can select profitable trades
out of sample.

## Safety Boundary

- No model promotion was authorized.
- No live trading was authorized.
- No broker execution was authorized.
- No capital allocation was authorized.
- No commit or push was performed.

## Artifacts

- `trading_system/models/gc_model_diagnostics.py`
- `tools/gc_model_diagnostics.py`
- `tools/validate_phase49.py`
- `schemas/gc_model_diagnostics_report.schema.json`
- `configs/models/gc-model-diagnostics-report.json`

## Verification

- `python -m pytest tests\models\test_gc_model_diagnostics.py -q`: PASS, `2 passed`.
- `python -m pytest tests\models\test_gc_model_diagnostics_cli.py tests\research\test_phase49_validator.py -q`: PASS, `2 passed in 73.26s`.
- `python -m pytest tests\models\test_first_real_gc_model.py tests\models\test_train_gc_first_real_model_cli.py tests\models\test_gc_model_diagnostics.py tests\models\test_gc_model_diagnostics_cli.py tests\research\test_phase48_validator.py tests\research\test_phase49_validator.py tests\datasets\test_dataset_contracts.py tests\datasets\test_dataset_factory.py tests\research\test_gc_pretraining_readiness.py -q`: PASS, `25 passed in 60.78s`.
- `python tools\validate_phase49.py`: PASS, `Phase 49 artifacts validated`.
- `python -m py_compile trading_system\datasets\contracts.py trading_system\datasets\factory.py trading_system\research\gc_pretraining_readiness.py trading_system\models\first_real_gc_model.py trading_system\models\gc_model_diagnostics.py tools\train_gc_first_real_model.py tools\validate_phase48.py tools\gc_model_diagnostics.py tools\validate_phase49.py`: PASS.

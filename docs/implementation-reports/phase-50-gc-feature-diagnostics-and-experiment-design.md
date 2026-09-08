# Phase 50 GC Feature Diagnostics And Experiment Design

## Summary

Phase 50 adds feature and regime diagnostics for the Phase 48 first real GC
model after Phase 49 blocked promotion.

This phase does not train a new model. It explains where the current
tree-derived feature set appears unstable and what experiments should come
next.

## Inputs

- Dataset build manifest: `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- Rows parquet: `market-data/gc-30m-real/f9d3c1b0d02da255/rows.parquet`
- First real model run: `configs/models/gc-first-real-model-run.json`
- Phase 49 diagnostics: `configs/models/gc-model-diagnostics-report.json`

## Result

- status: `EXPERIMENT_DESIGN_REQUIRED`
- diagnostic_focus: `FEATURE_AND_REGIME_STABILITY`
- promotion_allowed: `false`
- recommended experiments:
  - `FAILED_TRADE_CLUSTER_REVIEW`
  - `ORDER_FLOW_FEATURE_STABILITY_REVIEW`
  - `REGIME_FILTER_RESEARCH`
  - `THRESHOLD_STABILITY_REVIEW`

## Top Drift Features

The largest TRAIN-to-TEST feature shifts are:

- `close`: test drift z `7.787515337207615`
- `atr_14`: test drift z `3.396467398858739`
- `of_trades_sum_14`: test drift z `0.3778381792161452`
- `seconds_with_trades`: test drift z `0.3677018871004252`
- `of_trades`: test drift z `0.23648995491917835`

## Trading Interpretation

The model was trained mostly on a lower-price and lower-volatility era and then
tested on a very different gold regime. That makes absolute price (`close`) and
raw volatility (`atr_14`) suspicious as direct model inputs.

The next research pass should prefer normalized features:

- returns instead of absolute price
- ATR percentile/regime instead of raw ATR
- order-flow features normalized by volume/activity
- separate diagnostics for long and short candidates

## Regime Notes

- TEST long candidates had positive average R, while TEST short candidates had
  negative average R.
- Order-flow delta sign alone did not separate outcomes strongly.
- ATR high regime dominates TEST rows, which means volatility-regime stability
  needs a dedicated check before stronger models.

## Safety Boundary

- No model promotion was authorized.
- No live trading was authorized.
- No broker execution was authorized.
- No capital allocation was authorized.
- No commit or push was performed.

## Artifacts

- `trading_system/models/gc_feature_diagnostics.py`
- `tools/gc_feature_diagnostics.py`
- `tools/validate_phase50.py`
- `schemas/gc_feature_diagnostics_report.schema.json`
- `configs/models/gc-feature-diagnostics-report.json`

## Verification

- `python -m pytest tests\models\test_gc_feature_diagnostics.py -q`: PASS, `2 passed`.
- `python -m pytest tests\models\test_gc_feature_diagnostics_cli.py tests\research\test_phase50_validator.py -q`: PASS, `2 passed in 26.64s`.
- `python -m pytest tests\models\test_gc_feature_diagnostics.py tests\models\test_gc_feature_diagnostics_cli.py tests\research\test_phase50_validator.py -q`: PASS, `4 passed in 29.99s`.
- `python tools\validate_phase50.py`: PASS, `Phase 50 artifacts validated`.
- `python -m py_compile trading_system\models\gc_feature_diagnostics.py tools\gc_feature_diagnostics.py tools\validate_phase50.py`: PASS.

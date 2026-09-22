# Phase 53: GC Normalized Model Stability Review

## Purpose

Phase 53 stress-tests the Phase 52 normalized GC model before any promotion discussion.

The model had a small positive TEST result, but this phase checks whether that result is stable across:

- calendar months
- LONG vs SHORT candidates
- volatility regimes
- nearby probability thresholds

This phase does not retrain a model.

## Method

The report reloads the locked Phase 46 rows and scores TEST rows with the saved Phase 52 model coefficients.

Because Phase 52 stores coefficients on standardized features, Phase 53 reconstructs the TRAIN-only imputation and standardization from the locked TRAIN split. TEST rows are transformed using those TRAIN statistics only.

## Overall TEST Result

- Rows: `57584`
- Accuracy: `0.4408342595165324`
- Expected R per candidate: `0.00038432494158456814`
- Expected R per selected trade: `0.0010412122999861571`
- Selected trade rate: `0.36911294804112255`

The overall TEST result is slightly positive, matching Phase 52.

## Direction Stability

LONG:

- Rows: `28792`
- Expected R per candidate: `0.01354722019934434`
- Expected R per selected trade: `0.04227742943632368`
- Target precision: `0.5114892694558856`

SHORT:

- Rows: `28792`
- Expected R per candidate: `-0.012778570316175205`
- Expected R per selected trade: `-0.030586133223320017`
- Target precision: `0.47335605619752263`

Interpretation:

The model's positive TEST result is mainly carried by LONG candidates. SHORT candidates are not acceptable as-is.

## Volatility Stability

LOW volatility:

- Expected R per candidate: `-0.0020082638580663616`
- Expected R per selected trade: `-0.0023661617534488917`

MID volatility:

- Expected R per candidate: `0.0008112487018551749`
- Expected R per selected trade: `0.0014875504743397207`

HIGH volatility:

- Expected R per candidate: `0.0008284562660481121`
- Expected R per selected trade: `0.005983905698466881`

Interpretation:

The model is weak in LOW volatility and slightly positive in MID/HIGH volatility.

## Threshold Stability

Threshold `0.45`:

- Expected R per candidate: `0.0005547459260050184`
- Selected trade rate: `0.7451722700750208`

Threshold `0.50`:

- Expected R per candidate: `0.00038432494158456814`
- Selected trade rate: `0.36911294804112255`

Threshold `0.55`:

- Expected R per candidate: `-0.0005158404625912664`
- Selected trade rate: `0.08278341205890526`

Interpretation:

The edge is not robust to a higher threshold. That means we should not rely on the selected threshold yet.

## Conclusion

The normalized model is better than the first real model, but it is not stable enough for promotion.

The next research phase should test:

- LONG-only variant
- LOW-volatility exclusion or separate regime model
- walk-forward retraining instead of one static TRAIN fit
- threshold selection stability across rolling validation windows

## Promotion Boundary

Promotion remains blocked:

- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_normalized_model_stability_report.schema.json`
- Module: `trading_system/models/gc_normalized_model_stability.py`
- CLI: `tools/gc_normalized_model_stability.py`
- Validator: `tools/validate_phase53.py`
- Report: `configs/models/gc-normalized-model-stability-report.json`
- Tests:
  - `tests/models/test_gc_normalized_model_stability.py`
  - `tests/models/test_gc_normalized_model_stability_cli.py`
  - `tests/research/test_phase53_validator.py`

## Verification

```powershell
python -m pytest tests\models\test_gc_normalized_model_stability.py tests\models\test_gc_normalized_model_stability_cli.py tests\research\test_phase53_validator.py -q
python tools\validate_phase53.py
```

Result:

```text
4 passed
Phase 53 artifacts validated
```

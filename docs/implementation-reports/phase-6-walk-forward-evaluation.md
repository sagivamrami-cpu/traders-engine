# Phase 6 Walk Forward Evaluation Report

## Scope

Phase 6 adds research-only walk-forward evaluation, prediction payload creation,
calibration metrics, and promotion-gate reporting.

It does not implement live model serving, backtesting, broker integration,
capital allocation, deployment, shadow trading, paper trading, or production
promotion.

## Files

- schemas/model_evaluation_report.schema.json: evaluation report contract
- configs/evaluation/walk-forward-policy.yaml: chronological evaluation policy
- trading_system/evaluation: prediction payloads, metrics, walk-forward evaluation, and promotion gate
- tests/evaluation: contract, metric, walk-forward, promotion, and validator tests
- tools/validate_phase6.py: deterministic Phase 6 validator

## Tests

- `python -m pytest tests/evaluation -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`

## Decisions

- Walk-forward windows are expanding and chronological.
- Majority baseline predictions are one-hot and marked `LOW_COVERAGE`.
- Calibration metrics include Brier score and expected calibration error for `TARGET_FIRST`.
- Promotion is blocked regardless of metric output.
- Missing human, shadow, paper, and cost/fill evidence are explicit blocked reasons.

## Unresolved Risks

- No real vertical-slice dataset exists.
- No calibrated logistic or boosted model exists.
- No shadow or paper trading evidence exists.
- No costs/fills evaluation exists.
- No human promotion approval record exists.

## Next Phase

Phase 7 should add a model card and research registry package that records
training, evaluation, known limitations, blocked promotion reasons, and rollback
metadata. It must remain research-only until real data and human approval exist.

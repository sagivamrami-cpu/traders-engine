# Phase 54: GC Walk-Forward Retraining Experiments

## Goal

Convert the Phase 53 stability findings into a bounded walk-forward retraining experiment plan.

This phase does not promote a model and does not claim live trading edge. It defines the experiment matrix and gates required before a heavier retraining run.

## Inputs

- `configs/models/gc-normalized-model-stability-report.json`
- `configs/models/gc-normalized-feature-model-run.json`
- `configs/models/gc-normalized-feature-candidates-report.json`

## Outputs

- `schemas/gc_walk_forward_experiments_report.schema.json`
- `trading_system/models/gc_walk_forward_experiments.py`
- `tools/gc_walk_forward_experiments.py`
- `tools/validate_phase54.py`
- `configs/models/gc-walk-forward-experiments-report.json`
- `docs/implementation-reports/phase-54-gc-walk-forward-retraining-experiments.md`
- `agent-exchange/status/2026-09-07-phase-54-gc-walk-forward-retraining-experiments.md`

## Test Plan

1. Add unit tests for report construction from a stability-report fixture.
2. Add schema rejection tests for promotion flags.
3. Add CLI tests that write a sanitized report without local paths.
4. Add validator tests against the repository artifacts.
5. Generate the real Phase 54 report.
6. Run focused tests, validator, compile checks, secret scan, and git diff checks.

## Acceptance Criteria

- The report prioritizes LONG plus MID/HIGH volatility retraining because Phase 53 showed LONG positive and SHORT/LOW-volatility weakness.
- The report includes an all-candidate comparator and diagnostic-only SHORT/LOW-volatility experiments.
- Compute is bounded before heavier training: finite windows, stride, epochs, validation months, and minimum rows.
- Model promotion, live trading, broker execution, capital allocation, and edge claims remain blocked.
- No raw data, local paths, API keys, or secrets are written.

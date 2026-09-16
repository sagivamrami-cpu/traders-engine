# Phase 55: Execute Bounded Walk-Forward Retraining

## Goal

Run the bounded walk-forward retraining experiments defined in Phase 54.

This phase executes research retraining windows and reports results. It does not export a promoted model and does not authorize live trading.

## Inputs

- `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- `market-data/gc-30m-real/<dataset>/rows.parquet`
- `configs/models/gc-normalized-feature-candidates-report.json`
- `configs/models/gc-walk-forward-experiments-report.json`

## Outputs

- `schemas/gc_bounded_walk_forward_retraining_run.schema.json`
- `trading_system/models/gc_bounded_walk_forward_retraining.py`
- `tools/run_gc_bounded_walk_forward_retraining.py`
- `tools/validate_phase55.py`
- `configs/models/gc-bounded-walk-forward-retraining-run.json`
- `docs/implementation-reports/phase-55-execute-bounded-walk-forward-retraining.md`
- `agent-exchange/status/2026-09-07-phase-55-execute-bounded-walk-forward-retraining.md`

## Test Plan

1. Add unit tests using a small chronological fixture.
2. Add schema rejection tests for promotion flags.
3. Add CLI tests that run a tiny bounded walk-forward job.
4. Add validator tests against the repository artifacts.
5. Run the real bounded experiment with the Phase 54 budget.
6. Verify tests, validator, compile checks, secret scan, raw-data staging guard, and git diff checks.

## Acceptance Criteria

- Training windows are chronological.
- Each test month trains only on rows before the validation window.
- Threshold selection uses validation rows only.
- Feature normalization is fitted per window on training rows only.
- Primary and comparator experiments are both executed.
- Promotion, live trading, broker execution, capital allocation, and edge claims remain blocked.

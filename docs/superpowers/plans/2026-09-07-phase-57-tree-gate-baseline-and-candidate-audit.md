# Phase 57: Tree Gate Baseline and Candidate Audit

## Goal

Create a conservative rule-only tree baseline and candidate gate audit.

The baseline must not pretend to know manual tree stages that are not implemented yet. Missing typed gates produce `UNKNOWN`, and any mandatory unknown stage leads to `WAIT`.

## Inputs

- `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- `market-data/gc-30m-real/<dataset>/rows.parquet`
- `configs/models/gc-tree-translation-gap-review.json`

## Outputs

- `schemas/gc_tree_gate_baseline_audit.schema.json`
- `trading_system/models/gc_tree_gate_baseline.py`
- `tools/gc_tree_gate_baseline_audit.py`
- `tools/validate_phase57.py`
- `configs/models/gc-tree-gate-baseline-audit.json`
- `docs/implementation-reports/phase-57-tree-gate-baseline-and-candidate-audit.md`
- `agent-exchange/status/2026-09-07-phase-57-tree-gate-baseline-and-candidate-audit.md`

## Test Plan

1. Add unit tests for gate trace construction.
2. Add schema rejection tests for promotion flags.
3. Add CLI tests using a small local parquet fixture.
4. Add validator tests against repository artifacts.
5. Generate the real audit.
6. Verify focused tests, validator, compile checks, secret scan, raw-data staging guard, and git diff checks.

## Acceptance Criteria

- The audit includes all 14 TR runtime stages.
- Missing typed stages are `UNKNOWN`, not silently passed.
- Candidate-level sample traces include pass/block/unknown reasons.
- Final rule-only baseline actions are limited to `WAIT` or `NO_TRADE` until typed gates exist.
- Additional flat model training remains blocked.
- Model promotion, live trading, broker execution, capital allocation, and edge claims remain blocked.

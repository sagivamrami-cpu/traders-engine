# Phase 41 Approved Roll Label Split Gates

Status:
IMPLEMENTED_PENDING_CLAUDE_REVIEW

## Summary

Phase 41 converts the human-approved and Claude-accepted Phase 40 decisions
into enforceable research-gate metadata.

This phase closes the following contract gates for v1 research only:

- `ORDER_FLOW_SOURCE_DECISION`
- `ROLL_POLICY`
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`

It does not build datasets, labels, splits, features, models, or training runs.

## Implemented Decisions

- D5-final: research-only GC contract identity with
  `contract_identity_status: UNDECLARED_PENDING_RESEARCH`.
- D6-final: research-only order-flow source approval for
  `gc/GCext_of_1m.parquet`, bounded to `volume`, `delta`, and `trades`;
  `cvd` and cumulative-delta remain blocked.
- D7-final: outcome-contract label with `ATR(14)` closed-bar risk unit,
  `1.0 * R` target, `1.0 * R` stop, 8-bar 30m horizon, next-bar-open entry,
  ambiguous same-bar outcomes excluded, and HHLL blocked as primary label.
- D8-final: chronological walk-forward only, no random split, purge overlapping
  labels, 8-bar embargo, fold-local transform fitting, and consistent 2017
  exclusion using the tested order-flow mask function.

## Remaining Gates

The pretraining readiness report remains blocked with:

- `SESSION_CALENDAR`
- `MISSING_BAR_POLICY`
- `DATASET_IDENTITY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
- `REAL_DATASET_NOT_BUILT`

## Verification

Commands run:

- `python -m pytest tests\research\test_gc_label_split_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
- `python tools\validate_gc_label_split_policy.py --policy configs\research\gc-label-split-policy.yaml`
- `python tools\gc_pretraining_readiness.py --contract configs\datasets\gc-30m-real-dataset-contract.yaml --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist configs\research\real-data-readiness-checklist.yaml --training-policy configs\models\baseline-training-policy.yaml --groq-phase24-review agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md --groq-phase24-intake agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`
- `python tools\validate_phase39.py`
- `python -m pytest tests\research\test_gc_order_flow_row_mask_cumulative_policy.py tests\research\test_gc_pretraining_readiness.py -q`

Results:

- `14 passed`
- `8 passed`
- label/split policy validator emitted sanitized JSON
- readiness remains `BLOCKED`
- `training_start_allowed: false`
- `dataset_construction_allowed: false`
- `blocking_reviews: []`
- Claude Code review verdict:
  `ACCEPT_WITH_NOTES`

## Boundaries

Still not approved:

- dataset construction
- real dataset materialization
- model training
- model promotion
- live trading
- broker execution
- capital allocation
- CVD/cumulative-delta features
- HHLL primary labels
- random time-series splits

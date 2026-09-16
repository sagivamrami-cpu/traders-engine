# Phase 42 GC Session Calendar Registration

Status:
IMPLEMENTED_PENDING_CLAUDE_REVIEW

## Summary

Phase 42 registers `cme-globex-metals-research-v1` as the GC research
session calendar and removes `SESSION_CALENDAR` from the pretraining gate
list.

This phase does not build datasets, labels, splits, features, models, or
training runs.

## Implemented

- Added `cme-globex-metals-research-v1` to `configs/data/session-calendar.yaml`.
- Added `cme_globex_daily_break` support in `resolve_session()`.
- Encoded normal GC Globex research hours:
  Sunday-Friday sessions, 17:00 CT open, 16:00 CT close, 16:00-17:00 CT daily
  break, with `America/Chicago` DST conversion.
- Added trade-date roll for Globex sessions.
- Recorded Databento `status` schema skip decision for this v1 path.
- Wired the dataset contract, bar/session/timestamp policy, label/split policy,
  construction policy, schemas, and validators to the registered calendar.
- Updated active GC metadata references from pending calendar id to
  `cme-globex-metals-research-v1`.

## Remaining Gates

Pretraining readiness remains blocked with:

- `MISSING_BAR_POLICY`
- `DATASET_IDENTITY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
- `REAL_DATASET_NOT_BUILT`

## Boundaries

Still not approved:

- dataset construction
- real dataset materialization
- real label construction
- real split construction
- model training
- model promotion
- live trading
- broker execution
- capital allocation
- CVD/cumulative-delta features
- HHLL primary labels
- random time-series splits

The calendar is research-only and not execution truth. Holidays, special
hours, historical venue halts, and unexplained gaps remain controlled by the
missing-bar policy and future dataset manifest gates.

## Verification

Commands run:

- `python -m pytest tests\data_foundation\test_sessions.py tests\data_foundation\test_phase1_configs.py tests\research\test_gc_session_calendar_construction_policy.py tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py tests\research\test_gc_label_split_policy.py tests\research\test_databento_gc_order_flow_profile.py::test_order_flow_profile_cli_outputs_sanitized_json tests\research\test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_cli_outputs_sanitized_json tests\research\test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_cli_outputs_sanitized_json -q`
- `python tools\validate_phase1.py`
- `python tools\validate_phase39.py`
- `python tools\gc_pretraining_readiness.py --contract configs\datasets\gc-30m-real-dataset-contract.yaml --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist configs\research\real-data-readiness-checklist.yaml --training-policy configs\models\baseline-training-policy.yaml --groq-phase24-review agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md --groq-phase24-intake agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`

Results:

- `37 passed`
- `Phase 1 artifacts validated`
- `Phase 39 artifacts validated`
- readiness remains `BLOCKED`
- `training_start_allowed: false`
- `dataset_construction_allowed: false`
- `blocking_reviews: []`

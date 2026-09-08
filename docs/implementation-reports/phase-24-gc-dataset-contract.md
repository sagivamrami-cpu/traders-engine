# Phase 24 GC Dataset Contract Implementation Report

## Summary

Implemented a fail-closed GC real-dataset contract. Phase 24 defines the candidate dataset recipe and required unresolved gates before any real dataset construction.

This phase does not resample bars, build features, construct labels, create training rows, train a model, query vendors, extract archives, promote models, deploy, live trade, execute broker actions, or allocate capital.

## Files

- `docs/superpowers/plans/2026-09-01-phase-24-gc-dataset-contract.md`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `trading_system/research/gc_real_dataset_contract.py`
- `tools/validate_gc_real_dataset_contract.py`
- `tools/validate_phase24.py`
- `tests/research/test_gc_real_dataset_contract.py`
- `tests/research/test_phase24_validator.py`

## Contract Decisions

- `candidate_timeframe` is `30m`; `timeframe_status` is now `BASELINE_APPROVED_V1_NOT_MODEL_FINAL` after the D1 v1 bar-boundary decision.
- `dataset_construction_allowed` is false.
- `training_allowed` is false.
- `construction_authorized_by` is an empty list.
- `ORDER_FLOW_SOURCE_DECISION` remains open and required before order-flow features or a real dataset.
- `DATASET_IDENTITY`, `CANONICAL_OHLCV_INPUT`, and `CANONICAL_ORDER_FLOW_INPUT` remain explicit unsatisfied gates.
- D1 is recorded as `APPROVED_V1_NOT_DATASET_AUTHORIZED`: v1 uses fixed UTC 30m half-open bars with `available_at=bar_end_utc`, but this does not authorize dataset construction or training.
- D1 covers closed-bar features only; non-closed-bar or streaming features remain `UNDEFINED_BLOCKED_PENDING_NEW_HUMAN_DECISION`.
- D2 is recorded as `APPROVED_SOURCE_STRATEGY_V1_NOT_CALENDAR_AUTHORIZATION`: the source strategy is approved, but the session-calendar implementation gate remains unsatisfied.
- D4 is recorded as `POLICY_ONLY_NO_FILL_NOT_GATE_SATISFIED`: OHLCV no-invented-fill direction only; gap detection and drop-vs-mark implementation remain blocked until the session calendar is approved and missing-bar handling is implemented per feature family.
- D5 is recorded as `BLOCKER_TEMPLATE_ONLY_NOT_GATE_SATISFIED`: roll/identity blocker direction only; no dated/parent/continuous identity is chosen.
- `OPTIONS_SOURCE_DECISION` remains deferred to v2 and does not authorize options queries.
- Macro features remain blocked pending per-source decision and leakage gates.
- `ORDER_FLOW_ERA_MAP` is required and currently unsatisfied.
- The 2017 damaged-aggressor interval uses half-open UTC `[start, end)` semantics from `2017-01-01T00:00:00Z` to `2017-06-01T00:00:00Z`.
- CVD and cumulative delta remain blocked pending PIT, fold-local, era-gapped policy.
- Archived/precomputed CVD is explicitly blocked through `USE_ARCHIVED_CVD_COLUMN` and `INGEST_PRECOMPUTED_CVD`.
- `gold_orderflow_4h.csv` and `hhll_*` remain reference-only and cannot be used as training rows or trade-contract labels.
- `MAP_GC_TO_XAUUSD`, `MAP_GC_TO_GLD`, `JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS`, and `USE_REVISED_MACRO_SERIES` remain blocked.
- `INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES` remains blocked.

## Verification

- `python -m pytest tests\research\test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_config_is_fail_closed -q`: RED then PASS.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_schema_accepts_fail_closed_payload -q`: RED then PASS.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_report_preserves_blocked_readiness -q`: RED then PASS.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_cli_outputs_sanitized_blocked_json tests\research\test_phase24_validator.py -q`: RED then PASS.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py tests\research\test_phase24_validator.py -q`: PASS, 6 passed.
- `python tools\validate_phase24.py`: PASS, `Phase 24 artifacts validated`.
- `python tools\validate_phase26.py`: PASS after Groq Phase 23-26 denial-list hardening.

## Remaining Blockers

- Session calendar implementation for CME Globex metals, including era-versioned holidays, maintenance breaks, DST membership, and scheduled-vs-observed closure handling.
- Missing-bar policy by feature family.
- Roll policy and contract identity.
- Dataset identity.
- Canonical OHLCV input.
- Canonical order-flow input.
- Full order-flow era map.
- CVD/cumulative-feature recomputation policy.
- Outcome label contract for the selected timeframe.
- Split and embargo policy.
- Explicit future human authorization for dataset construction.
- D4/D5 filename confirmation from the human is useful for audit clarity, but neither record closes a gate.

## Next Phase

Route Phase 24 to Claude Code and Groq for implementation review. After review intake, Codex should fix any blockers before asking the human to decide the remaining dataset gates.

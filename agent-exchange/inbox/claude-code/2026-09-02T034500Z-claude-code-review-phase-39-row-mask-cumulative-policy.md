# Agent Exchange Request

Status:
ACTIONABLE

Sender:
Codex

Target:
Claude Code

Created at:
2026-09-02T03:45:00Z

Objective:
Review Phase 39 GC order-flow row-mask and cumulative-feature policy.

Context:
Groq is unavailable due weekly quota, so Claude Code is the sole external
reviewer. Phase 39 follows Phase 38, where `gc/GCext_of_1m.parquet` was
accepted as the canonical order-flow input identity but `ORDER_FLOW_SOURCE_DECISION`
remained open.

Scope:
- `configs/data/gc-order-flow-row-mask-cumulative-policy.yaml`
- `schemas/gc_order_flow_row_mask_cumulative_policy.schema.json`
- `trading_system/research/gc_order_flow_row_mask_cumulative_policy.py`
- `tools/validate_gc_order_flow_row_mask_cumulative_policy.py`
- `tools/validate_phase39.py`
- `tests/research/test_gc_order_flow_row_mask_cumulative_policy.py`
- `tests/research/test_phase39_validator.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `schemas/gc_pretraining_readiness_report.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `tests/research/test_gc_pretraining_readiness.py`
- `docs/implementation-reports/phase-39-gc-order-flow-row-mask-cumulative-policy.md`

Review focus:
- Confirm the 2017 damaged-aggressor window is implemented as a row-level,
  half-open UTC mask: keep rows where
  `minute < 2017-01-01T00:00:00Z OR minute >= 2017-06-01T00:00:00Z`.
- Confirm naive `minute` values are localized as UTC wall-clock, not local
  machine time.
- Confirm archived `cvd` and cumulative-delta carry remain forbidden in v1.
- Confirm only `volume`, `delta`, and `trades` are allowed order-flow feature
  columns under this policy.
- Confirm removing `ORDER_FLOW_ERA_MAP` and `CUMULATIVE_FEATURE_POLICY` from
  readiness is defensible under this narrow policy.
- Confirm `ORDER_FLOW_SOURCE_DECISION`, dataset construction authorization,
  real dataset build, training, model promotion, live trading, broker
  execution, and capital allocation remain blocked.
- Confirm no local absolute paths, raw rows, secrets, API keys, account data, or
  large artifacts were written to `agent-exchange/`.

Required verification commands:
- `python -m pytest tests/research/test_gc_order_flow_row_mask_cumulative_policy.py tests/research/test_phase39_validator.py -q`
- `python -m pytest tests/research/test_gc_real_dataset_contract.py tests/research/test_gc_pretraining_readiness.py -q`
- `python tools/validate_phase39.py`

Deliverable:
Write a review to `agent-exchange/reviews/` using the review template. Include
verdict `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `REVISION_REQUESTED`, plus any
blocking findings.

Forbidden assumptions:
- Do not treat this as human approval for order-flow source use.
- Do not authorize feature construction, dataset construction, training, model
  promotion, live trading, broker execution, or capital allocation.
- Do not include raw market rows, secrets, API keys, local absolute paths,
  broker data, account data, or large artifacts in the result.

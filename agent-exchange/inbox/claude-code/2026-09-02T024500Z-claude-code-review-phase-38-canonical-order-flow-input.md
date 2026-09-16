# Agent Exchange Request

Status:
ACTIONABLE

Sender:
Codex

Target:
Claude Code

Created at:
2026-09-02T02:45:00Z

Objective:
Review Phase 38 canonical GC order-flow input manifest and dataset-contract
wiring.

Context:
Groq is unavailable due weekly quota, so Claude Code is the sole external
reviewer for this phase. Codex selected `gc/GCext_of_1m.parquet` as the
canonical order-flow input identity because it gives the longest available
`volume`, `delta`, `trades`, `minute` history and avoids archived `cvd`
ingestion. This is an input-identity record only; it must not approve source
use or feature construction.

Scope:
- `configs/data/gc-canonical-order-flow-input-manifest.yaml`
- `schemas/gc_canonical_order_flow_input_manifest.schema.json`
- `trading_system/research/gc_canonical_order_flow_input_manifest.py`
- `tools/validate_gc_canonical_order_flow_input_manifest.py`
- `tools/validate_phase38.py`
- `tests/research/test_gc_canonical_order_flow_input_manifest.py`
- `tests/research/test_phase38_validator.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `trading_system/research/gc_real_dataset_contract.py`
- `tests/research/test_gc_real_dataset_contract.py`
- `docs/implementation-reports/phase-38-gc-canonical-order-flow-input-manifest.md`

Review focus:
- Confirm `ORDER_FLOW_SOURCE_DECISION` remains open and is not satisfied by
  this manifest.
- Confirm `CANONICAL_ORDER_FLOW_INPUT` is the only readiness gate intentionally
  removed by this phase.
- Confirm `gc/GCext_of_1m.parquet` is a defensible canonical input identity
  choice for longest non-archived-CVD order-flow history.
- Confirm archived `cvd` ingestion remains forbidden.
- Confirm the 2017 damaged aggressor-side window remains excluded and row-level
  masking is still required before `ORDER_FLOW_ERA_MAP` can be satisfied.
- Confirm no dataset construction, order-flow feature build, training, local
  paths, raw rows, or secrets were introduced.

Required verification commands:
- `python -m pytest tests/research/test_gc_canonical_order_flow_input_manifest.py tests/research/test_phase38_validator.py -q`
- `python -m pytest tests/research/test_gc_real_dataset_contract.py tests/research/test_gc_pretraining_readiness.py -q`
- `python tools/validate_phase38.py`

Deliverable:
Write a review to `agent-exchange/reviews/` using the review template. Include
verdict `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `REVISION_REQUESTED`, plus any
blocking findings.

Forbidden assumptions:
- Do not treat this as human approval for order-flow source use.
- Do not authorize feature construction, dataset construction, training, model
  promotion, live trading, broker execution, or capital allocation.
- Do not read or write raw market rows into `agent-exchange/`.
- Do not include secrets, API keys, local absolute paths, broker data, or large
  artifacts in the result.

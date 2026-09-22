# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T13:45:01Z

Status:
REVIEW_ONLY

Objective:
Risk-review Phase 26 GC order-flow era-map for leakage, false readiness, and insufficient era-policy gates.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-26-gc-order-flow-era-map.md`
- `schemas/gc_order_flow_era_map.schema.json`
- `trading_system/research/gc_order_flow_era_map.py`
- `tools/inspect_gc_order_flow_era_map.py`
- `tools/validate_phase26.py`
- `tests/research/test_gc_order_flow_era_map.py`
- `tests/research/test_phase26_validator.py`
- `docs/implementation-reports/phase-26-gc-order-flow-era-map.md`
- `agent-exchange/status/2026-09-01T134400Z-codex-phase-26-implementation-result.md`

Required inputs:
- `agent-exchange/protocol.md`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `docs/implementation-reports/phase-25-gc-pretraining-readiness.md`

Contracts:
- The era map must not imply order-flow feature readiness.
- CVD must remain blocked until fold-local/PIT/era-gap recomputation exists.
- Dataset construction and training must remain blocked.
- The 2017 damaged-aggressor window must remain half-open UTC and not be treated as the complete era policy.

Deliverables:
Write a review file under `agent-exchange/reviews/` using `agent-exchange/templates/review.md`.

Verification commands:
- `python tools/validate_phase26.py`

Out of scope:
- Do not modify source code.
- Do not query vendors.
- Do not build datasets, features, labels, or models.

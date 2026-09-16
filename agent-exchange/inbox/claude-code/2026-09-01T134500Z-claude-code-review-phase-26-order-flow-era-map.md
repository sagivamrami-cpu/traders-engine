# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T13:45:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 26 GC order-flow era-map implementation for contract correctness, path redaction, and fail-closed behavior.

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
- `AGENTS.md`
- `agent-exchange/README.md`
- `agent-exchange/protocol.md`

Contracts:
- Phase 26 may profile all Parquet files but must not construct features or datasets.
- Local archive paths must be redacted.
- Raw market-data rows must not be emitted.
- `ORDER_FLOW_SOURCE_DECISION` must remain open.
- Dataset construction and training must remain blocked.

Deliverables:
Write a review file under `agent-exchange/reviews/` using `agent-exchange/templates/review.md`.

Verification commands:
- `python tools/validate_phase26.py`

Out of scope:
- Do not modify source code.
- Do not query vendors.
- Do not build datasets, features, labels, or models.

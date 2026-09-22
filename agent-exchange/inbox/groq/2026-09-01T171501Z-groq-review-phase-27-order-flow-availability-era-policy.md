# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T17:15:01Z

Status:
REVIEW_REQUESTED

Priority:
HIGH

Objective:
Challenge-review Phase 27 GC order-flow availability-era policy candidate.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-27-gc-order-flow-availability-era-policy.md`
- `schemas/gc_order_flow_availability_era_policy.schema.json`
- `trading_system/research/gc_order_flow_availability_era_policy.py`
- `tools/inspect_gc_order_flow_availability_era_policy.py`
- `tools/validate_phase27.py`
- `tests/research/test_gc_order_flow_availability_era_policy.py`
- `tests/research/test_phase27_validator.py`
- `docs/implementation-reports/phase-27-gc-order-flow-availability-era-policy.md`

Challenge focus:
- Find any path where this policy candidate could be mistaken for a satisfied `ORDER_FLOW_ERA_MAP`.
- Find any path where file-range regimes could be treated as row-level masks.
- Find any path where archived `cvd` or cumulative features could be copied into training rows.
- Find any path where canonical GC/GCall/GCext or OHLCV inputs are implicitly selected.
- Find any path where `dataset_construction_allowed` or `training_allowed` could become true without human D1-D9 completion.

Forbidden assumptions:
- No source approval, feature approval, row-level masking, canonical input selection, dataset construction, model training, vendor query, purchase, upload, live trading, broker execution, or capital allocation.
- Do not include secrets, raw market rows, local absolute paths, or large artifacts.

Verification command:
- `python tools/validate_phase27.py`

Expected output:
Write review to `agent-exchange/reviews/` with blocking findings first, safer wording recommendations, commands run, and whether Codex may accept this phase as a blocked policy candidate only.

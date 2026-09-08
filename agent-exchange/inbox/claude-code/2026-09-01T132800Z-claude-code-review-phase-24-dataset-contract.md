# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T13:28:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 24 GC real-dataset contract implementation for schema/config/module/CLI/test consistency and fail-closed behavior.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-24-gc-dataset-contract.md`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `trading_system/research/gc_real_dataset_contract.py`
- `tools/validate_gc_real_dataset_contract.py`
- `tools/validate_phase24.py`
- `tests/research/test_gc_real_dataset_contract.py`
- `tests/research/test_phase24_validator.py`
- `docs/implementation-reports/phase-24-gc-dataset-contract.md`
- `agent-exchange/status/2026-09-01T132700Z-codex-phase-24-implementation-result.md`

Required inputs:
- `AGENTS.md`
- `agent-exchange/README.md`
- `agent-exchange/protocol.md`
- `agent-exchange/reviews/2026-09-01T174500Z-claude-code-review-phase-24-human-dataset-decisions.md`

Contracts:
- Phase 24 is contract-only.
- No dataset builder may be introduced.
- `dataset_construction_allowed` must be false.
- `training_allowed` must be false.
- `construction_authorized_by` must be empty.
- 30m must remain candidate-only.
- Options must remain deferred to v2.
- Macro must remain per-source leakage-gated.
- Order-flow source decision must remain open.
- `ORDER_FLOW_ERA_MAP` must be required and unsatisfied.
- Exclusion intervals must use half-open UTC `[start, end)` semantics.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, API keys, raw market-data payloads, or local absolute data paths

Deliverables:
Write a review file under `agent-exchange/reviews/` using `agent-exchange/templates/review.md`. Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.

Verification commands:
- `python tools/validate_phase24.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not modify source code.
- Do not query vendors.
- Do not read raw market-data rows.
- Do not construct datasets, features, labels, or models.

Notes:
Check whether `tools/validate_phase24.py` correctly avoids recursive invocation of `tests/research/test_phase24_validator.py`.

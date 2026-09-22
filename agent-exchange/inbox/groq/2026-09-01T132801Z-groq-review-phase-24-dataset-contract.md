# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T13:28:01Z

Status:
REVIEW_ONLY

Objective:
Risk-review Phase 24 GC real-dataset contract implementation for leakage, false readiness, and missing hard blockers.

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
- `agent-exchange/protocol.md`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `agent-exchange/reviews/2026-09-01T174500Z-claude-code-review-phase-24-human-dataset-decisions.md`

Contracts:
- Phase 24 must be schema/config/validator only.
- It must not create a data builder, feature builder, label builder, or training path.
- Dataset construction and training must remain blocked.
- The 2017 damaged interval must be half-open UTC `[start, end)`.
- `ORDER_FLOW_ERA_MAP`, timestamp role, CVD policy, macro policy, label contract, split/embargo, and construction authorization must remain hard unsatisfied gates.

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
Look specifically for any path that would allow `BUILD_REAL_DATASET`, `BUILD_ORDER_FLOW_FEATURES`, CVD, macro, HHLL labels, 4H CSV ingestion, options queries, or training before explicit future approvals.

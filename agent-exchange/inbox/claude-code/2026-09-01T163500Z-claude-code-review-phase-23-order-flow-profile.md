# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T16:35:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 23 GC order-flow profile implementation for correctness, test coverage, schema contract, and integration with existing readiness gates.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-23-gc-order-flow-profile.md`
- `configs/data/databento-gc-order-flow-source-metadata.yaml`
- `configs/data/gc-order-flow-quality-gates.yaml`
- `schemas/databento_gc_order_flow_profile.schema.json`
- `trading_system/research/databento_gc_order_flow_profile.py`
- `tools/inspect_databento_gc_order_flow_zip.py`
- `tools/validate_phase23.py`
- `tests/research/test_databento_gc_order_flow_profile.py`
- `tests/research/test_phase23_validator.py`
- `docs/implementation-reports/phase-23-gc-order-flow-profile.md`
- `agent-exchange/status/2026-09-01T163000Z-codex-phase-23-implementation-result.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.

Contracts:
- Phase 23 is profile-only.
- `ORDER_FLOW_SOURCE_DECISION` must remain open.
- Options remain deferred/open and must not be queried.
- No raw market data, local absolute archive paths, secrets, or API keys may appear in repo or exchange files.
- The 4H CSV and HHLL files must remain reference-only and blocked from training rows.
- 30m must be a baseline candidate only, not a frozen training timeframe.
- CVD/cumulative features must remain blocked pending PIT/fold-local/era-gap policy.
- Macro features must remain per-source leakage-gated.

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include severity-ordered findings and exact commands run.

Verification commands:
- `python -m pytest tests/research/test_databento_gc_order_flow_profile.py tests/research/test_phase23_validator.py -q`
- `python tools/validate_phase23.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not call Databento APIs.
- Do not read or print raw market-data rows.
- Do not approve feature construction, dataset construction, training, model promotion, live trading, broker execution, or capital allocation.
- Do not mutate the working tree.

Notes:
Copy/paste prompt for Claude Code:

```text
You are Claude Code reviewing Phase 23 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/claude-code/2026-09-01T163500Z-claude-code-review-phase-23-order-flow-profile.md`.

Your job is review-only. Check the Phase 23 order-flow profile code, schema, configs, CLI, validator, tests, and report. Verify this remains profile-only, keeps `ORDER_FLOW_SOURCE_DECISION` open, blocks feature/dataset/training actions, keeps 4H CSV and HHLL reference-only, treats 30m only as a candidate, and does not leak local paths or raw data. Run the listed commands and write your review to `agent-exchange/reviews/`.
```

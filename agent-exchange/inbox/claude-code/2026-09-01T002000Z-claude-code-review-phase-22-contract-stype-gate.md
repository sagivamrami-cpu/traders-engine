# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T00:20:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 22 Databento contract/stype decision gate for implementation correctness and test coverage.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-22-databento-contract-stype-decision-gate.md`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`
- `schemas/databento_gc_contract_stype_decision.schema.json`
- `trading_system/research/databento_contract_stype_decision.py`
- `tools/validate_databento_gc_contract_stype_decision.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `tests/research/test_databento_contract_stype_decision.py`
- `docs/implementation-reports/phase-22-databento-contract-stype-decision-gate.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.

Contracts:
- Open contract/stype template must validate but must not approve online cost preflight.
- Approved contract/stype decisions must be scoped to `COST_PREFLIGHT_ONLY`.
- Approved decisions must require approver, timestamp, evidence, selected mode, and selected symbols.
- `XAUUSD` and `GLD` must be rejected.
- Phase 21 online CLI must require `--contract-stype-decision` before constructing a Databento client.

Non-negotiables:
- no API keys in repo or exchange
- no Databento data download or purchase
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no `timeseries.get_range`

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include severity-ordered findings and exact commands run.

Verification commands:
- `python -m pytest tests/research/test_databento_contract_stype_decision.py -q`
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_databento_contract_stype_decision.py tests/research/test_phase21_validator.py -q`
- `python tools/validate_phase21.py`

Out of scope:
- Do not call Databento APIs with a real key.
- Do not approve any order-flow/options source decision.

Notes:
Copy/paste prompt for Claude Code:

```text
You are Claude Code reviewing Phase 22 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/claude-code/2026-09-01T002000Z-claude-code-review-phase-22-contract-stype-gate.md`.

Your job is review-only. Check the contract/stype decision schema, loader, CLI validator, tests, and Phase 21 CLI integration. Verify that the open template does not approve online cost preflight, approved decisions are cost-preflight-only, XAUUSD/GLD are rejected, and online mode cannot construct a Databento client without a valid decision. Run the verification commands and write your review to `agent-exchange/reviews/`.
```

# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T00:25:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 22 Databento contract/stype decision gate for market-data identity, hidden approval, and vendor-risk issues.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-22-databento-contract-stype-decision-gate.md`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`
- `schemas/databento_gc_contract_stype_decision.schema.json`
- `trading_system/research/databento_contract_stype_decision.py`
- `tools/validate_databento_gc_contract_stype_decision.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `docs/implementation-reports/phase-22-databento-contract-stype-decision-gate.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.

Contracts:
- Contract/stype approval is for Databento cost preflight only.
- Dated raw symbol, parent futures, and continuous front-month modes must not be treated as equivalent.
- `GC`, `XAUUSD`, and `GLD` must remain separate identities.
- Options parent remains unconfirmed.
- No data purchase, download, training, promotion, live trading, broker execution, or capital allocation is approved.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no Databento data download or purchase
- no `timeseries.get_range`

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include findings by severity and exact commands run.
- State whether Phase 22 is safe as a decision gate before a real-key online cost estimate.

Verification commands:
- `python tools/validate_phase21.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not call Databento APIs with a real key.
- Do not choose a contract/stype mode for the human.
- Do not approve order-flow or options source decisions.

Notes:
Copy/paste prompt for Groq:

```text
You are Groq reviewing Phase 22 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/groq/2026-09-01T002500Z-groq-review-phase-22-contract-stype-gate.md`.

Your job is review-only. Challenge the Databento contract/stype decision gate from market-data and hidden-approval angles. Verify that dated raw symbol, parent futures, and continuous front-month modes remain separate; GC/XAUUSD/GLD are not conflated; options parent remains unconfirmed; and approval is scoped only to cost preflight, not purchase/download/features/training/trading. Run the listed commands if available and write your review to `agent-exchange/reviews/`.
```

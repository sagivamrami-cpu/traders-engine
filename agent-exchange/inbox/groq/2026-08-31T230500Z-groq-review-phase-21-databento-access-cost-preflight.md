# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T23:05:00Z

Status:
REVISION_REQUESTED

Objective:
Challenge the Phase 21 Databento preflight from market-data, vendor-risk, symbol-identity, cost, and hidden-approval perspectives.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-21-databento-access-cost-preflight.md`
- `configs/data/databento-gc-vendor-preflight.yaml`
- `schemas/databento_gc_vendor_preflight.schema.json`
- `trading_system/research/databento_vendor_preflight.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md` before review.
- Treat all credentials and vendor account details as unavailable and forbidden to serialize.

Contracts:
- Phase 21 is a metadata/cost-estimate gate only.
- Databento remains a candidate source for order flow and options, not approved spend.
- GC, XAUUSD, and GLD must stay separate identities.
- Options parent symbol remains unconfirmed and must not be queried.
- `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` remain open.

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
- Findings must be ordered by severity.
- Include exact commands run and pass/fail results.
- Include any required wording, gate, or policy hardening.

Verification commands:
- `python tools/validate_phase21.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not approve order-flow or options source decisions.
- Do not call Databento APIs with a real key.
- Do not change repo files.

Notes:
Copy/paste prompt for Groq:

```text
You are Groq reviewing Phase 21 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/groq/2026-08-31T230500Z-groq-review-phase-21-databento-access-cost-preflight.md`.

Your job is to challenge the plan and implementation, not implement. Focus on market-data assumptions, Databento vendor/cost risk, whether raw symbol `GC` is too ambiguous, GC vs XAUUSD vs GLD separation, options parent symbol handling, hidden approval risks, and whether any status wording can be misread as permission to buy data, build features, train, or trade. Run the verification commands if available. Write your result to `agent-exchange/reviews/` with verdict `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`, severity-ordered findings, commands run, and concrete gate-hardening recommendations.
```

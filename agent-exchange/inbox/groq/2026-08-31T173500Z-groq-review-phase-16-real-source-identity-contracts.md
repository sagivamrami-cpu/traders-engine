# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T17:35:00Z

Status:
REVIEW_ONLY

Objective:
Review the Phase 16 real-source identity contract plan for contradictions,
missing adversarial cases, fixture leakage paths, and hidden production
approval risks before or after Claude Code implements it.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`
- `docs/implementation-reports/phase-15-real-data-safety-hardening.md`
- `agent-exchange/status/2026-08-31T170000Z-codex-phase-15-acceptance.md`
- `agent-exchange/protocol.md`
- `configs/data/local-csv-onboarding-template.yaml`
- `configs/data/symbol-map.yaml`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/research/source_bundle.py`
- `trading_system/research/offline_dry_run.py`
- `trading_system/research/readiness.py`
- `tests/data_foundation/`
- `tests/research/`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Current accepted Phase 15 state.
- Phase 16 plan file listed above.

Contracts:
- Groq reviews only. Do not make approval, merge, production-readiness, or
  architecture ownership decisions.
- Look specifically for ways a non-fixture source can inherit fixture source,
  graph, dataset, regime, symbol, or calendar identities.
- Look for paths where a mere file reference under `agent-exchange/decisions/`
  could be mistaken for human approval.
- Look for cases where order-flow/options deferral could be mistaken for data
  source approval.
- Look for CLI bypasses around source bundle, retention, readiness, or dry-run
  guards.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no raw market data, secrets, credentials, or account data in review output

Deliverables:
- Review file under `agent-exchange/reviews/` using
  `agent-exchange/templates/review.md`.
- Status must be `REVIEW_READY_FOR_CODEX`.
- Findings should be numbered and severity-ranked.
- For every finding include:
  - observed issue
  - risk
  - concrete failing scenario
  - recommended fix
  - whether it blocks Phase 16 acceptance
- Include a "No issues found" section only if no blocking issue exists.

Verification commands:
- `python tools/validate_phase15.py`
- `python tools/real_data_readiness.py`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`

Out of scope:
- Writing implementation code.
- Approving production data.
- Approving model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Claude Code has not finished yet, review the plan as a pre-implementation
architecture risk review. If Claude Code has finished, review both the plan and
implementation result.

Prompt to paste into Groq:
You are Groq reviewing the `traders-engine` repo. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T173500Z-groq-review-phase-16-real-source-identity-contracts.md`.
Review Phase 16 for contradiction, fixture leakage, fake approval, defer-as-
approval, and CLI bypass risks. Do not implement code. Write your review to
`agent-exchange/reviews/` with `Status: REVIEW_READY_FOR_CODEX`.

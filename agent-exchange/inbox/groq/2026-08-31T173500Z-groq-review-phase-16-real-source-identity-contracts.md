# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T17:35:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Review the Phase 16 real-source identity contract plan for contradictions,
missing adversarial cases, fixture leakage paths, and hidden production
approval risks before or after Claude Code implements it.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`
- `agent-exchange/status/2026-08-31T180000Z-codex-phase-16-implementation-status.md`
- `agent-exchange/status/2026-08-31T181000Z-codex-phase-16-acceptance.md`
- `docs/implementation-reports/phase-16-real-source-identity-contracts.md`
- `configs/data/source-identity-policy.yaml`
- `schemas/source_identity_policy.schema.json`
- `schemas/source_bundle_validation.schema.json`
- `trading_system/data_foundation/source_identity.py`
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
- Codex Phase 16 implementation status and acceptance files if present.

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
Codex implemented Phase 16 directly because no Claude Code completion result
was present. Review both the plan and the implementation artifacts.

Prompt to paste into Groq:
You are Groq reviewing the `traders-engine` repo. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T173500Z-groq-review-phase-16-real-source-identity-contracts.md`.
Review Phase 16 plan and implementation for contradiction, fixture leakage,
fake approval, defer-as-approval, and CLI bypass risks. Do not implement code.
Write your review to `agent-exchange/reviews/` with
`Status: REVIEW_READY_FOR_CODEX`.

# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T20:05:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 18 real-source onboarding preflight for hidden approval,
decision-record bypasses, fixture leakage, raw-data/path leakage, and any path
that lets `REAL_SOURCE_PENDING_HUMAN_DECISION` enter fixture onboarding,
source-bundle, dry-run, dataset, model-training, promotion, live trading,
broker execution, or capital-allocation flows.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`
- `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`
- `agent-exchange/status/2026-08-31T193500Z-codex-phase-17-acceptance.md`
- `agent-exchange/inbox/claude-code/2026-08-31T200000Z-claude-code-phase-18-real-source-onboarding-preflight.md`
- `agent-exchange/protocol.md`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/research/source_bundle.py`
- `trading_system/research/intake_packet.py`
- `trading_system/research/readiness.py`
- `trading_system/data_foundation/source_identity.py`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Current accepted Phase 17 state.
- Phase 18 plan and Claude Code request listed above.

Contracts:
- Groq reviews only. Do not make approval, merge, production-readiness, or
  architecture ownership decisions.
- Look for any output path that can expose raw CSV rows, absolute local paths,
  secrets, account identifiers, or private source details.
- Look for any path where a decision reference, preflight report, `DEFERRED`
  decision, or pending source identity can be mistaken for production approval.
- Look for bypasses around source identity, readiness, retention, source bundle,
  and dry-run gates.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no raw market data, secrets, credentials, account identifiers, or absolute
  user paths in review output

Deliverables:
- Review file under `agent-exchange/reviews/` using
  `agent-exchange/templates/review.md`.
- Status must be `REVIEW_READY_FOR_CODEX`.
- Findings should be numbered and severity-ranked.
- For every finding include observed issue, risk, failing scenario,
  recommended fix, and whether it blocks Phase 18 acceptance.

Verification commands:
- `python tools/validate_phase17.py`
- `python tools/real_data_readiness.py`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`

Out of scope:
- Writing implementation code.
- Approving production data.
- Approving model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Phase 18 implementation status exists, review both the plan and
implementation. If it does not, review the plan as a pre-implementation risk
review.

Prompt to paste into Groq:
You are Groq reviewing the `traders-engine` repo. Pull the latest branch
`plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T200500Z-groq-review-phase-18-real-source-onboarding-preflight.md`.
Review Phase 18 for hidden approval, decision-record bypasses, deferred-as-
approval mistakes, raw-data leakage, absolute-path leakage, fixture leakage,
and any route where pending real-source identity enters onboarding/bundle/dry-
run/dataset/model/trading paths. Do not implement code. Write your review to
`agent-exchange/reviews/` with `Status: REVIEW_READY_FOR_CODEX`.

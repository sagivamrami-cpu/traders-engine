# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T18:35:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 17 human real OHLCV intake packet design for path leakage,
hidden approval, raw-data leakage, and bypasses around readiness/source
identity before or after Claude Code implements it.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- `docs/implementation-reports/phase-16-real-source-identity-contracts.md`
- `agent-exchange/status/2026-08-31T181000Z-codex-phase-16-acceptance.md`
- `agent-exchange/inbox/claude-code/2026-08-31T183000Z-claude-code-phase-17-human-real-ohlcv-intake.md`
- `agent-exchange/protocol.md`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `trading_system/data_foundation/csv_inspection.py`
- `trading_system/data_foundation/source_identity.py`
- `trading_system/research/readiness.py`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Current accepted Phase 16 state.
- Phase 17 plan file listed above.

Contracts:
- Groq reviews only. Do not make approval, merge, production-readiness, or
  architecture ownership decisions.
- Look for any packet, CLI, schema, template, or agent-exchange path that can
  expose raw CSV rows, absolute local paths, secrets, account identifiers, or
  private source details.
- Look for any path where an intake packet, template, or decision reference can
  be mistaken for production approval.
- Look for bypasses around source identity, readiness, retention, and dry-run
  gates.

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
- For every finding include:
  - observed issue
  - risk
  - concrete failing scenario
  - recommended fix
  - whether it blocks Phase 17 acceptance
- Include a "No issues found" section only if no blocking issue exists.

Verification commands:
- `python tools/validate_phase16.py`
- `python tools/real_data_readiness.py`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`

Out of scope:
- Writing implementation code.
- Approving production data.
- Approving model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Phase 17 implementation status exists, review both the plan and
implementation. If it does not, review the plan as a pre-implementation risk
review.

Prompt to paste into Groq:
You are Groq reviewing the `traders-engine` repo. Pull the latest branch
`plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T183500Z-groq-review-phase-17-human-real-ohlcv-intake.md`.
Review Phase 17 for raw-data leakage, absolute-path leakage, fake approval,
decision-reference-as-approval, and gate bypass risks. Do not implement code.
Write your review to `agent-exchange/reviews/` with
`Status: REVIEW_READY_FOR_CODEX`.

# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T21:15:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 19 local-only real-source bundle preparation for hidden approval,
preflight bypasses, fixture-path bypasses, raw-data leakage, path leakage,
decision-record leakage, dry-run/dataset/training bypasses, and any wording
that could be mistaken as production approval.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-19-local-only-real-source-bundle.md`
- `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`
- `agent-exchange/status/2026-08-31T205000Z-codex-phase-18-acceptance.md`
- `agent-exchange/inbox/claude-code/2026-08-31T211000Z-claude-code-phase-19-local-only-real-source-bundle.md`
- `agent-exchange/protocol.md`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `trading_system/research/real_source_onboarding.py`
- `trading_system/research/source_bundle.py`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/data_foundation/storage_policy.py`
- `trading_system/research/readiness.py`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Accepted Phase 18 state at commit `4e8ca04`
- Phase 19 plan and Claude Code request listed above.

Contracts:
- Groq reviews only. Do not implement code and do not approve production data.
- Look for any path where a Phase 18 preflight, source identity, decision
  record, retention decision, local manifest, or bundle payload can be mistaken
  for approval to run dry-run, build datasets, train models, promote models,
  trade live, execute broker actions, allocate capital, deploy, retain raw data,
  copy raw data, mutate raw data, or upload raw data.
- Look for raw CSV rows, absolute local paths, secrets, account identifiers,
  private source details, or unredacted decision details in planned outputs.
- Check whether `REAL_SOURCE_PENDING_HUMAN_DECISION` remains blocked from
  fixture onboarding and fixture source-bundle/dry-run paths.
- Check whether the proposed schema and tests actually enforce the local-only
  boundary.

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
  recommended fix, and whether it blocks Phase 19 acceptance.

Verification commands:
- `python tools/validate_phase18.py`
- `python tools/real_data_readiness.py`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`

Out of scope:
- Writing implementation code.
- Approving production data.
- Approving raw retention.
- Approving model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Phase 19 implementation status exists by the time you start, review both
the plan and implementation. If it does not, review the plan as a
pre-implementation risk review.

Prompt to paste into Groq:
You are Groq reviewing Phase 19 in the `traders-engine` repo. Pull the latest
branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T211500Z-groq-review-phase-19-local-only-real-source-bundle.md`.
Review for hidden approval, preflight bypasses, fixture-path bypasses, raw data
or absolute path leakage, decision-record leakage, and any route from local
manifest preparation into dry-run/dataset/training/promotion/trading/broker or
capital-allocation flows. Do not implement code. Write your review under
`agent-exchange/reviews/` with `Status: REVIEW_READY_FOR_CODEX`.

# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T21:10:00Z

Status:
ACTIONABLE

Objective:
Implement Phase 19: local-only real-source bundle preparation. The goal is to
consume a Phase 18 records-present preflight and produce sanitized local
manifest metadata for a real OHLCV source, without running dry-run, building a
dataset, training a model, promoting a model, live trading, broker execution,
capital allocation, or deployment.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-19-local-only-real-source-bundle.md`
- `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`
- `trading_system/research/real_source_onboarding.py`
- `trading_system/research/source_bundle.py`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/data_foundation/storage_policy.py`
- `trading_system/data_foundation/normalization.py`
- `trading_system/research/readiness.py`
- `schemas/real_source_onboarding_preflight.schema.json`
- `agent-exchange/protocol.md`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `tests/research/`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Accepted Phase 18 commit: `4e8ca04`
- Phase 19 implementation plan:
  `docs/superpowers/plans/2026-08-31-phase-19-local-only-real-source-bundle.md`

Contracts:
- Start with tests from the Phase 19 plan.
- Implement a new real-source local bundle path; do not open fixture onboarding
  or fixture source-bundle validation to real-source identity.
- Require Phase 18 preflight status
  `PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED`.
- Emit only sanitized output: no raw CSV rows, no absolute local paths, no
  secrets, no broker/account identifiers, no private source details.
- Keep `production_allowed=false`.
- Keep `allowed_next_actions=[]`.
- Keep `dry_run_summary=null`.
- Do not call offline dry-run, dataset builders, training code, model
  promotion, broker code, or deployment code.
- Real-source local manifest may include hashes, row count, canonical symbol,
  raw symbol, and observation interval, but `raw_file` must be
  `LOCAL_PATH_REDACTED`.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no approval from agent-authored files
- no committed real CSV payloads or absolute user paths

Deliverables:
- Implement every task in
  `docs/superpowers/plans/2026-08-31-phase-19-local-only-real-source-bundle.md`.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.
- List every changed file and exact verification output.

Verification commands:
- `python -m pytest tests/research/test_real_source_local_bundle.py tests/research/test_phase19_validator.py -v`
- `python tools/validate_phase19.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `foreach ($p in 0..19) { python "tools/validate_phase$p.py"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }`
- `git diff --check`

Out of scope:
- Fetching vendor data.
- Committing real CSV data.
- Retaining/copying/uploading raw CSV payloads.
- Running dry-run on real-source data.
- Building production datasets.
- Training models.
- Model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Codex is already implementing the same task in this working tree, do not
duplicate edits. Leave a verification/status result instead.

Prompt to paste into Claude Code:
You are Claude Code implementing Phase 19 in the `traders-engine` repo. Pull
the latest branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/protocol.md`, and
`agent-exchange/inbox/claude-code/2026-08-31T211000Z-claude-code-phase-19-local-only-real-source-bundle.md`.
Implement the Phase 19 plan exactly. Start with tests. Keep the implementation
local-only and sanitized: no raw CSV rows, no absolute local paths, no dry-run,
no dataset construction, no training, no broker/trading/capital actions. Write
your result under `agent-exchange/status/` with status
`IMPLEMENTED_AWAITING_CODEX_REVIEW`.

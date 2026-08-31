# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T20:00:00Z

Status:
ACTIONABLE

Objective:
Implement Phase 18: real-source onboarding preflight. The goal is to let the
project consume valid human decision records and source metadata to produce a
redacted preflight report, while ensuring pending real-source identity cannot
enter fixture onboarding, source bundle validation, dry-run, dataset
construction, or model training paths.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`
- `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`
- `agent-exchange/status/2026-08-31T193500Z-codex-phase-17-acceptance.md`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/research/source_bundle.py`
- `trading_system/research/intake_packet.py`
- `trading_system/research/readiness.py`
- `trading_system/data_foundation/source_identity.py`
- `configs/data/real-ohlcv-source-metadata-template.yaml`
- `configs/research/real-data-readiness-checklist.yaml`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `tests/data_foundation/`
- `tests/research/`

Required inputs:
- Phase 18 implementation plan:
  `docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`
- Current accepted Phase 17 intake packet and source identity gate.
- Existing human approval boundary in `agent-exchange/protocol.md`.

Contracts:
- Start with tests. Do not implement production code before failing tests.
- Preflight output must be sanitized: no raw CSV rows, no absolute local paths,
  no secrets, no broker/account identifiers.
- `REAL_SOURCE_PENDING_HUMAN_DECISION` must not pass through fixture
  onboarding, source bundle validation, or dry-run.
- Preflight may permit only local manifest/bundle preparation as a future next
  action; it must never permit production dataset construction, production
  training, model promotion, live trading, broker execution, capital
  allocation, or deployment.
- Readiness must remain `BLOCKED` for production dataset construction.
- `DEFERRED` order-flow/options decisions are not approvals.

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
  `docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.

Verification commands:
- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_real_source_onboarding_preflight.py tests/research/test_phase18_validator.py -v`
- `python tools/validate_phase17.py`
- `python tools/validate_phase18.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

Out of scope:
- Fetching vendor data.
- Writing or committing real CSV payloads.
- Building a production dataset.
- Training a production model.
- Model promotion.
- Broker integration.
- Live trading.
- Deployment.

Notes:
When finished, leave a result file and stop. Codex will inspect the diff,
incorporate Groq review, rerun verification, and decide acceptance.

Codex clarification:
The Phase 18 positive preflight test must use a temporary project root with a
temporary `configs/data/symbol-map.yaml` containing the real test mapping. Do
not add real symbols to the committed symbol map.

Prompt to paste into Claude Code:
You are Claude Code working in the `traders-engine` repo. Pull the latest
branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and then
`agent-exchange/inbox/claude-code/2026-08-31T200000Z-claude-code-phase-18-real-source-onboarding-preflight.md`.
Implement Phase 18 exactly from
`docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`.
Use tests first. Do not approve production data, do not build production
datasets, do not train models, do not commit raw CSVs, and do not emit absolute
user paths. When complete, write a result under `agent-exchange/status/` with
status `IMPLEMENTED_AWAITING_CODEX_REVIEW` and include exact verification
output.

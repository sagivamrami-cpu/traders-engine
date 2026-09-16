# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T18:30:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Implement Phase 17: human real OHLCV intake packet. The goal is to let a human
run a local CSV validation/intake command that emits sanitized JSON without raw
CSV payloads, absolute paths, or production approval.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- `docs/implementation-reports/phase-16-real-source-identity-contracts.md`
- `agent-exchange/status/2026-08-31T181000Z-codex-phase-16-acceptance.md`
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- `configs/data/local-csv-onboarding-template.yaml`
- `configs/data/source-identity-policy.yaml`
- `schemas/local_csv_inspection_report.schema.json`
- `schemas/source_identity_policy.schema.json`
- `trading_system/data_foundation/csv_inspection.py`
- `trading_system/data_foundation/source_identity.py`
- `trading_system/research/readiness.py`
- `tests/research/`

Required inputs:
- Phase 17 implementation plan:
  `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- Current accepted Phase 16 source identity contract.
- Existing human approval boundary in `agent-exchange/protocol.md`.

Contracts:
- Start with tests. Do not implement production code before failing tests.
- CLI and packet output must not include raw CSV rows or absolute local file
  paths.
- CLI and packet output may include `raw_file_sha256`, row count, raw symbols,
  and first/last observed timestamps.
- A human decision reference is not approval by itself.
- The packet must keep `production_allowed=false`.
- Readiness must remain `BLOCKED` unless valid human decision records exist
  under `agent-exchange/decisions/`.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no raw CSV payloads, secrets, broker credentials, account data, private
  identifiers, or absolute user paths in committed files or agent-exchange
  outputs
- no approval from agent-authored files

Deliverables:
- Implement every task in
  `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`.
- New sanitized packet module, schema, CLI, metadata template, human decision
  template, validator, tests, and implementation report.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.

Verification commands:
- `python -m pytest tests/research/test_intake_packet.py -v`
- `python -m pytest tests/research/test_phase17_validator.py -v`
- `python tools/validate_phase16.py`
- `python tools/validate_phase17.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

Out of scope:
- Fetching vendor data.
- Approving a real source.
- Writing or committing real CSV payloads.
- Building a production dataset.
- Training a production model.
- Broker integration.
- Live trading.
- Model promotion.
- Deployment.

Notes:
Codex implemented this phase directly before a Claude Code result was posted.
No Claude Code action is currently required unless Codex opens a revision
request.

Original instruction before Codex implementation:
When finished, leave a result file and stop. Codex will inspect the diff and
rerun verification before accepting.

Prompt to paste into Claude Code:
You are Claude Code working in the `traders-engine` repo. Pull the latest
branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and then
`agent-exchange/inbox/claude-code/2026-08-31T183000Z-claude-code-phase-17-human-real-ohlcv-intake.md`.
Implement Phase 17 exactly from
`docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`.
Use tests first. Do not approve real data, do not commit raw CSVs, and do not
emit absolute user paths. When complete, write a result under
`agent-exchange/status/` with status `IMPLEMENTED_AWAITING_CODEX_REVIEW` and
include exact verification output.

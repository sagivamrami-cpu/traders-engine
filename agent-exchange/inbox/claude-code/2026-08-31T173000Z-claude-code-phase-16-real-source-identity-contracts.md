# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T17:30:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Implement Phase 16: real-source identity contracts. The goal is to prevent
fixture identity leakage into real-source metadata while allowing the project
to progress toward OHLCV-only research without hidden production approval.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`
- `docs/implementation-reports/phase-15-real-data-safety-hardening.md`
- `agent-exchange/status/2026-08-31T170000Z-codex-phase-15-acceptance.md`
- `configs/data/local-csv-onboarding-template.yaml`
- `configs/data/symbol-map.yaml`
- `configs/data/raw-data-retention-policy.yaml`
- `schemas/raw_source_manifest.schema.json`
- `schemas/source_bundle_validation.schema.json`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/data_foundation/normalization.py`
- `trading_system/research/source_bundle.py`
- `trading_system/research/offline_dry_run.py`
- `tools/run_local_csv_dry_run.py`
- `tests/data_foundation/`
- `tests/research/`

Required inputs:
- Phase 16 implementation plan:
  `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`
- Current Phase 15 accepted behavior.
- Existing agent-exchange approval boundary.

Contracts:
- Start with tests. Do not implement production code before failing tests.
- Fixture identifiers such as `local-csv-ohlcv-fixture`, `TR_FIXTURE_SPY`,
  fixture graph ids, and fixture dataset ids are valid only for fixture mode.
- Real-source metadata must not reuse fixture identifiers.
- Real-source metadata must include a human decision reference under
  `agent-exchange/decisions/`, but Phase 16 must not treat that reference as
  production approval by itself.
- No Phase 16 output may unblock production dataset construction, production
  training, model promotion, live trading, broker execution, deployment, or
  capital allocation.
- Order-flow and options may be explicitly deferred in future decisions, but
  defer is not approval.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no real CSV payloads, secrets, broker credentials, account data, or absolute
  user paths in committed files
- no approval from agent-authored files

Deliverables:
- Implement every task in
  `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`.
- New source identity policy/config/schema/module.
- Tests covering fixture mode, blocked real-source fixture leakage, missing
  human decision refs, bundle payload identity, and dry-run guard behavior.
- `tools/validate_phase16.py`.
- Implementation report under `docs/implementation-reports/`.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.

Verification commands:
- `python -m pytest tests/data_foundation/test_source_identity.py -v`
- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_offline_dry_run.py -v`
- `python -m pytest tests/research/test_phase16_validator.py -v`
- `python tools/validate_phase15.py`
- `python tools/validate_phase16.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

Out of scope:
- Fetching vendor data.
- Approving any real data source.
- Writing or committing real CSV payloads.
- Building a production dataset.
- Training a production model.
- Broker integration.
- Live trading.
- Model promotion.
- Deployment.

Notes:
When finished, leave a result file and stop. Codex will inspect the diff and
rerun verification before accepting.

Codex note:
Codex implemented this task directly because no Claude Code completion result
was present when execution continued. The implementation and verification are
recorded in
`agent-exchange/status/2026-08-31T180000Z-codex-phase-16-implementation-status.md`.

Prompt to paste into Claude Code:
You are Claude Code working in the `traders-engine` repo. Read `AGENTS.md`,
`agent-exchange/README.md`, `agent-exchange/protocol.md`, and then this inbox
request. Implement Phase 16 exactly from
`docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`.
Use tests first, keep production dataset construction blocked, do not approve
real data, and do not commit raw CSVs or secrets. When complete, write a result
under `agent-exchange/status/` with status
`IMPLEMENTED_AWAITING_CODEX_REVIEW` and include exact verification output.

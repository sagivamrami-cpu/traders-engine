# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T15:30:00Z

Status:
ACTIONABLE

Objective:
Implement Phase 15: real-data safety hardening based on Groq review findings
F1/F2/F4/F5/F6/F7/F9/F11/F12. The goal is to prevent fixture contamination,
hidden approval, dry-run bypasses, and misleading readiness states before any
human real-data decision can unblock production dataset construction.

Scope:
- `agent-exchange/reviews/2026-08-31T151000Z-groq-review-phases-8-13-and-exchange.md`
- `agent-exchange/status/2026-08-31T152500Z-codex-groq-review-intake.md`
- `configs/data/symbol-map.yaml`
- `configs/data/local-csv-onboarding-template.yaml`
- `configs/research/real-data-readiness-checklist.yaml`
- `configs/research/real-data-decisions-template.yaml`
- `schemas/local_csv_inspection_report.schema.json`
- `schemas/real_data_decisions.schema.json`
- `schemas/real_data_readiness_report.schema.json`
- `trading_system/data_foundation/csv_inspection.py`
- `trading_system/data_foundation/csv_onboarding.py`
- `trading_system/data_foundation/normalization.py`
- `trading_system/data_foundation/storage_policy.py`
- `trading_system/features/market_state.py`
- `trading_system/datasets/factory.py`
- `trading_system/research/readiness.py`
- `trading_system/research/source_bundle.py`
- `trading_system/research/offline_dry_run.py`
- `tools/inspect_local_ohlcv_csv.py`
- `tools/onboard_ohlcv_csv.py`
- `tools/validate_local_source_bundle.py`
- `tools/run_local_csv_dry_run.py`
- `tools/real_data_readiness.py`
- `tests/data_foundation/`
- `tests/research/`

Required inputs:
- Groq review findings F1-F12.
- Current Phase 14 implementation accepted by Codex with follow-up hardening
  required.
- Existing agent-exchange approval boundary.

Contracts:
- Start with tests. Do not implement production code before failing tests.
- F2 is mandatory: an `APPROVED` readiness decision may satisfy an item only if
  every evidence path is a resolvable markdown file under
  `agent-exchange/decisions/` and that record contains approver, timestamp,
  scope, decision, and evidence fields. YAML in `configs/`, temp folders, or
  inbox/status/reviews must not produce `READY_FOR_PRODUCTION_DATASET`.
- Defer is not approval: introduce a distinct decision value for explicit
  defer/non-use, and do not allow it to satisfy source/vendor approval items.
- F1 is mandatory: non-fixture local CSV paths must not emit fixture-only ids
  such as `ohlcv-fixture-v1`, `TR_FIXTURE_SPY`, `fixture-candidate-dataset`,
  `FIXTURE_NEUTRAL`, or fixture graph identifiers. Fixture identifiers may be
  used only for committed fixture tests.
- F4 is mandatory: `run_local_csv_dry_run.py` must not bypass source bundle and
  retention validation. It should require a validated bundle path or delegate to
  `validate_local_source_bundle` before producing dry-run output.
- F5 is mandatory: CSV inspection must fail closed for blank `raw_symbol`,
  unknown symbols, invalid OHLC, duplicate timestamps, and
  `available_at < observed_at`. Inspection status must not imply bundle
  acceptance if only shape checks passed.
- F6 is mandatory: no report may say `READY_FOR_PRODUCTION_DATASET` while
  `blocked_actions` still includes `BUILD_PRODUCTION_TRAINING_DATASET`.
- F7 is mandatory: prevent accidental commit/leak of real CSV data and absolute
  user paths. Add gitignore/test or output-redaction behavior as appropriate.
- F11/F12 are follow-up hardening: fail closed on edited retention approvals and
  add adversarial dry-run tests for ordering, duplicates, timestamp parsing,
  large-enough training rows, and session/calendar edge cases where practical.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no committed real CSV data
- no secrets, broker credentials, account data, or raw market-data payloads
- no approval from agent-authored files

Deliverables:
- Phase 15 implementation plan under `docs/superpowers/plans/`.
- Tests covering the mandatory contracts above.
- Code/schema/config/docs changes needed to make the tests pass.
- Phase 15 validator `tools/validate_phase15.py`.
- Phase 15 implementation report under `docs/implementation-reports/`.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.

Verification commands:
- `python -m pytest tests/research/test_real_data_readiness.py -v`
- `python -m pytest tests/data_foundation -v`
- `python -m pytest tests/research -v`
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`
- `python tools/validate_phase14.py`
- `python tools/validate_phase15.py`
- `python tools/real_data_readiness.py`
- `python tools/real_data_readiness.py --decisions configs/research/real-data-decisions-template.yaml`
- `python tools/inspect_local_ohlcv_csv.py --help`
- `python tools/run_local_csv_dry_run.py --help`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -v`

Out of scope:
- Fetching vendor data.
- Approving a real source.
- Writing real CSV payloads.
- Broker integration.
- Live trading.
- Model promotion.
- Deployment.

Notes:
Keep changes scoped and conservative. If any Groq finding requires an
architectural decision before implementation, stop and write `BLOCKED` status
for Codex rather than inventing policy.

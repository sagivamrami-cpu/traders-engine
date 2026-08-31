# Phase 18 Real Source Onboarding Preflight Report

## Scope

Phase 18 adds a fail-closed real-source onboarding preflight. It can combine a
local OHLCV CSV, real-source metadata, and human decision records into a
sanitized preflight report, while keeping production dataset construction,
model training, model promotion, live trading, broker execution, and capital
allocation blocked.

It does not fetch vendor data, commit raw CSV payloads, build a production
dataset, train a model, promote a model, execute broker actions, or allocate
capital.

## Files

- `trading_system/research/real_source_onboarding.py`: builds redacted
  preflight reports from the Phase 17 intake packet and readiness decisions.
- `schemas/real_source_onboarding_preflight.schema.json`: validates preflight
  output and keeps path fields redacted.
- `tools/preflight_real_source_onboarding.py`: prints sanitized preflight JSON
  and fails closed with redacted error output.
- `tools/validate_phase18.py`: validates Phase 17 regression, focused tests,
  preflight schema, CLI redaction, and blocked readiness.
- `trading_system/data_foundation/csv_onboarding.py`: rejects non-fixture
  source identity before raw manifest creation.
- `trading_system/research/source_bundle.py`: returns schema-valid `BLOCKED`
  output for non-fixture source identity instead of entering dry-run.
- `trading_system/research/intake_packet.py`: accepts an optional
  `project_root` for temporary test policies and symbol maps.
- `trading_system/research/readiness.py`: accepts inline and multiline human
  decision record fields, requires inline decision values for approved/deferred
  evidence records, and rejects blank fields that run into the next field label.
- Tests under `tests/data_foundation/` and `tests/research/`.
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`:
  adds the preflight command and restates the non-production boundary.

## Tests

- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_real_source_onboarding_preflight.py tests/research/test_phase18_validator.py -v`
- `python tools/validate_phase17.py`
- `python tools/validate_phase18.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

## Decisions

- `REAL_SOURCE_PENDING_HUMAN_DECISION` is not accepted by fixture onboarding or
  source bundle validation.
- A preflight report can return `PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED`
  only when source identity, intake shape, and human decision records are
  present and valid. It still advertises no next actions in Phase 18.
- `DEFERRED` order-flow/options decisions can satisfy preflight completeness
  for local OHLCV preparation, but readiness remains `BLOCKED`.
- Markdown decision records must use inline `Decision: APPROVED`,
  `Decision: NOT_APPROVED`, or `Decision: DEFERRED`; YAML `APPROVED` and
  `DEFERRED` entries must cite matching markdown records.
- Every preflight path field is redacted as `LOCAL_PATH_REDACTED` or `null`.
- Nested readiness decision details are redacted in preflight output so
  approver names, scopes, and evidence paths cannot leak through sanitized
  reports.

## Unresolved Risks

- No real human decision records exist in this repository yet.
- No committed real symbol map entry exists yet.
- No real-source manifest/bundle implementation is opened in this phase.
- Production dataset construction and model training remain blocked.

## Next Phase

Phase 19 should define a local-only real-source manifest/bundle preparation
path that consumes this report-only preflight and still refuses production
dataset construction or model training.

# Phase 19 Local-Only Real Source Bundle Report

## Scope

Phase 19 adds a local-only, sanitized real-source bundle preparation path. It
consumes a Phase 18 records-present preflight
(`PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED`) and produces a redacted
manifest-like payload for a real OHLCV source: hashes, row count, canonical
and raw symbols, observation interval, and metadata identity fields, with
`raw_file` always `LOCAL_PATH_REDACTED` and the owner redacted.

Phase 19 does not run offline dry-run and does not train a model. It also does
not build datasets, promote models, retain/copy/upload raw CSVs, execute
broker actions, allocate capital, or deploy. `production_allowed` stays
`false`, `allowed_next_actions` stays empty, and `dry_run_summary` stays
`null` in every output. The fixture-only onboarding and source-bundle paths
remain closed to real-source identity.

## Files

- `trading_system/research/real_source_local_bundle.py`: local bundle builder
  gated on the Phase 18 preflight (new).
- `schemas/real_source_local_bundle.schema.json`: sanitized local bundle
  contract with status-conditional manifest rules and a strict redacted
  preflight summary shape (new).
- `tools/prepare_real_source_local_bundle.py`: CLI printing sorted sanitized
  JSON; sanitized error JSON on stderr (new).
- `tools/validate_phase19.py`: deterministic Phase 19 validator with Phase 18
  regression, blocked CLI coverage, and prepared-path CLI coverage (new).
- `tests/research/test_real_source_local_bundle.py`: blocked-default,
  records-present manifest, redaction, and CLI tests (new).
- `tests/research/test_phase19_validator.py`: validator smoke test (new).
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`:
  adds the Phase 19 CLI command and its non-approval warning (modified).

## Tests

- `python -m pytest tests/research/test_real_source_local_bundle.py tests/research/test_phase19_validator.py -v`
- `python tools/validate_phase19.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `foreach ($p in 0..19) { python "tools/validate_phase$p.py"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }`
- `git diff --check`

## Decisions

- A new `real_source_local_bundle` module was created instead of opening the
  fixture-only `csv_onboarding` / `source_bundle` paths to real sources; the
  Phase 18 gates on those paths are unchanged.
- The Phase 18 preflight status `PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED`
  is a hard precondition; any other preflight status yields `BLOCKED` with
  `PREFLIGHT_NOT_RECORDS_PRESENT` plus the preflight's own blocked reasons.
- The prepared status is named
  `LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED` so a successful preparation can
  never read as production readiness; blocked actions and empty next actions
  are baked into the schema as constants.
- Blocked fixture inputs are still schema-valid blocked outputs, while the
  prepared status requires `REAL_SOURCE_PENDING_HUMAN_DECISION` and
  `mode="REAL_SOURCE"`.
- Retention is forced to `BLOCKED` for Phase 19 even on prepared outputs:
  `retention_approved`, `raw_copy_allowed`, `raw_mutation_allowed`,
  `network_upload_allowed`, and `dry_run_output_allowed` are always `false`.
  `manifest_output_allowed` only permits the redacted metadata payload.
- The sanitized manifest redacts `raw_file` and the owner name; local paths
  never appear at any nesting level. The embedded Phase 18 preflight is reduced
  to status and blocked-action summary fields, so owner and decision-record
  values are not re-emitted through nested structures. The schema rejects
  additional nested preflight fields.
- Manifest preparation failures collapse to `BLOCKED` with
  `LOCAL_MANIFEST_PREPARATION_FAILED` rather than leaking exception text.

## Unresolved Risks

- No real human decision records exist; every committed-config invocation
  stays `BLOCKED`.
- No real symbol map entry exists in committed config; positive-path coverage
  uses temporary project roots only.
- Order-flow and options decisions remain `DEFERRED` in test fixtures; defer
  is not approval.
- The local manifest is prepared in memory and printed only; nothing is
  written to disk, so a later phase must define where human-reviewed
  manifests are stored.

## Next Phase

A later phase may consume a prepared local manifest to define a guarded
real-source research path (dataset gates still closed), but only after real
human decision records exist under `agent-exchange/decisions/` and Codex
routes that phase explicitly. Phase 19 deliberately stops at sanitized local
manifest preparation.

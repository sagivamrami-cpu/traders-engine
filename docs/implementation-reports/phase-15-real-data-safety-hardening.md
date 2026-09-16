# Phase 15 Real-Data Safety Hardening Report

## Scope

Phase 15 hardens the real-data path after Groq review. It prevents arbitrary
decision YAML files from satisfying readiness, separates defer from approval,
keeps production dataset construction blocked, strengthens local CSV inspection,
requires retention/bundle validation before dry-run CLI output, and blocks
non-fixture metadata from using fixture-only dry-run identities.

It does not approve a source, fetch vendor data, store raw CSV data, train a
production model, promote a model, integrate a broker, run live execution,
deploy, or allocate capital.

## Files

- `trading_system/research/readiness.py`: approved decisions must originate
  under `agent-exchange/decisions/` and reference existing markdown human
  decision records.
- `schemas/real_data_decisions.schema.json`: adds `DEFERRED`.
- `schemas/real_data_readiness_report.schema.json`: report version
  `real-data-readiness-report-0.3.0`.
- `trading_system/data_foundation/csv_inspection.py`: fail-closed inspection
  checks for blank symbols, unknown symbols, canonical mismatch, invalid OHLC,
  duplicate timestamps, and `available_at < observed_at`.
- `schemas/local_csv_inspection_report.schema.json`: inspection version
  `local-csv-inspection-report-0.2.0` and status
  `SHAPE_VALIDATED_NEEDS_BUNDLE_VALIDATION`.
- `tools/inspect_local_ohlcv_csv.py`: passes symbol-map validation into
  inspection.
- `trading_system/research/offline_dry_run.py`: keeps fixture graph/dataset
  identities behind a fixture-only guard.
- `tools/run_local_csv_dry_run.py`: requires `--retention-policy` and validates
  the source bundle before printing dry-run output.
- `trading_system/data_foundation/storage_policy.py`: edited storage roots now
  block manifest-only mode.
- `.gitignore`: ignores real CSV exports while allowing test fixtures.
- `tools/validate_phase9.py`, `tools/validate_phase13.py`,
  `tools/validate_phase15.py`: validators updated for hardened gates.
- Tests updated under `tests/data_foundation/`, `tests/research/`, and
  `tests/agent_exchange/`.

## Tests

- `python -m pytest tests/research/test_real_data_readiness.py -v`
- `python -m pytest tests/data_foundation/test_csv_inspection.py -v`
- `python -m pytest tests/research/test_offline_dry_run.py -v`
- `python -m pytest tests/data_foundation/test_storage_policy.py -v`
- `python -m pytest tests/agent_exchange/test_repository_hygiene.py -v`
- `python -m pytest tests/research/test_phase15_validator.py -v`
- `python tools/validate_phase9.py`
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`
- `python tools/validate_phase14.py`
- `python tools/validate_phase15.py`

## Decisions

- `APPROVED` decisions can satisfy readiness items only from a decision YAML
  under `agent-exchange/decisions/`.
- Every `APPROVED` decision evidence path must be an existing markdown file
  under `agent-exchange/decisions/` with approver, timestamp, scope, decision,
  and evidence fields.
- `DEFERRED` is a distinct decision value and does not satisfy source/vendor
  approval.
- The readiness report remains `BLOCKED` while
  `BUILD_PRODUCTION_TRAINING_DATASET` is still blocked.
- Inspection success is explicitly shape-only and still requires bundle
  validation.
- The direct dry-run CLI cannot bypass retention/source-bundle validation.

## Unresolved Risks

- Real-symbol identities, real graph ids, and non-fixture dataset ids are not
  implemented yet.
- No real historical CSV has been provided.
- No human decision records exist for production data, retention, source
  selection, order-flow, or options.
- Order-flow and options still need separate action gates before feature work.

## Next Phase

Phase 16 should introduce explicit real-source identity contracts: symbol-map
entry workflow, source id naming, graph id/version naming, dataset id/version
naming, and OHLCV-only research gating that does not require fake approvals for
order-flow or options.

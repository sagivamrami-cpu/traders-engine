# Phase 16 Real Source Identity Contracts Report

## Scope

Phase 16 introduces explicit source identity validation before local CSV
manifest, source bundle, and dry-run outputs. It separates committed fixture
metadata from future real-source metadata, blocks fixture identifiers in
real-source contexts, requires a human decision reference for real-source
metadata, and keeps all production actions blocked.

It does not approve any real source, fetch data, store raw CSV payloads, build
a production dataset, train a production model, promote a model, deploy, run
live trading, execute broker actions, or allocate capital.

## Files

- `configs/data/source-identity-policy.yaml`: defines fixture-only identifiers,
  real-source required metadata fields, forbidden fixture fragments, deferred
  producers, and blocked actions.
- `schemas/source_identity_policy.schema.json`: validates the source identity
  policy.
- `trading_system/data_foundation/source_identity.py`: loads policy and
  validates metadata identity.
- `trading_system/data_foundation/csv_onboarding.py`: rejects blocked source
  identity before raw manifest creation.
- `trading_system/research/source_bundle.py`: records source identity in bundle
  payloads and returns a schema-valid blocked bundle when identity is invalid.
- `schemas/source_bundle_validation.schema.json`: bumps the validation contract
  to `source-bundle-validation-0.2.0`, adds `source_identity`, and requires
  full raw manifest fields only for accepted dry-run bundles.
- `trading_system/research/offline_dry_run.py`: uses the source identity
  contract for the fixture-only dry-run guard.
- `tools/validate_phase16.py`: validates Phase 16 artifacts and runs Phase 15
  regression validation.
- Tests updated under `tests/data_foundation/` and `tests/research/`.

## Tests

- `python -m pytest tests/data_foundation/test_source_identity.py -v`
- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_offline_dry_run.py -v`
- `python -m pytest tests/research/test_phase16_validator.py -v`
- `python tools/validate_phase15.py`
- `python tools/validate_phase16.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`

## Decisions

- Fixture metadata is explicitly classified as `FIXTURE_ONLY`.
- Real-source metadata cannot reuse fixture source, symbol, graph, or dataset
  identifiers.
- A `human_decision_ref` path may identify the intended human decision record
  location, but it does not approve production usage by itself.
- Phase 16 may report `REAL_SOURCE_PENDING_HUMAN_DECISION`, but
  `production_allowed` remains `false`.
- The existing fixture dry-run path remains fixture-only.

## Unresolved Risks

- Real symbol-map entries are still not present.
- Human decision records are still not present under `agent-exchange/decisions/`.
- A real-source dry-run path is not implemented yet.
- Order-flow and options remain deferred pending explicit human decisions and
  separate data-source contracts.

## Next Phase

Phase 17 should define the real OHLCV intake packet: exact human decision
record format, real symbol-map entry workflow, sanitized metadata template, and
a no-raw-data validation command that a human can run against a local CSV.

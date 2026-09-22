# Phase 17 Human Real OHLCV Intake Packet Report

## Scope

Phase 17 adds a sanitized intake workflow for the first real OHLCV CSV. It lets
a human inspect source shape, derived metadata, source identity status, and
required decision records without committing raw market data or absolute local
paths.

It does not approve a real source, build a production dataset, train a
production model, promote a model, run live trading, execute broker actions, or
allocate capital.

## Files

- `trading_system/research/intake_packet.py`: composes CSV inspection and
  source identity validation into a redacted packet.
- `schemas/real_ohlcv_intake_packet.schema.json`: validates sanitized packet
  output.
- `tools/prepare_real_ohlcv_intake.py`: prints a schema-valid intake packet for
  a local CSV and metadata YAML and fails closed with sanitized error output.
- `configs/data/real-ohlcv-source-metadata-template.yaml`: blocked real-source
  metadata template with `UNSET_` sentinels.
- `agent-exchange/templates/human-decision-record.md`: human decision template
  that is explicitly not an approval record.
- `tools/validate_phase17.py`: validates schema, CLI output, path redaction,
  Phase 16 regression, and blocked readiness.
- `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`:
  points the human workflow at the new intake command and templates.
- Tests under `tests/research/`.

## Tests

- `python -m pytest tests/research/test_intake_packet.py -v`
- `python -m pytest tests/research/test_phase17_validator.py -v`
- `python tools/validate_phase16.py`
- `python tools/validate_phase17.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

## Decisions

- Intake packets expose derived metadata only: file hash, row count, symbols,
  observation range, validation statuses, blocked actions, and blocked reasons.
- Top-level and nested CSV paths are always replaced with
  `LOCAL_PATH_REDACTED`.
- A fixture-only source identity forces packet status `BLOCKED_INVALID_INPUT`;
  fixture packets cannot look like the real human-intake success lane.
- Only a real source with a valid human decision record can reach
  `BLOCKED_NEEDS_HUMAN_DECISION`, and that status still does not approve
  production usage.
- The required human decision records are listed in each packet, but records
  must still be completed by a human under `agent-exchange/decisions/`.
- The packet schema requires the exact safety-critical blocked-action and
  required-decision-record sets.
- Nested inspection output is closed by schema and its inspection id is rebuilt
  from redacted content, not from the original local CSV path.

## Unresolved Risks

- No real-source decision records exist yet.
- No approved production OHLCV vendor exists yet.
- Real symbol-map entries are still not present.
- Order-flow and options remain deferred unless humans explicitly approve or
  defer them in decision records.
- Lower-level inspect, onboard, bundle, and dry-run tools are not documented as
  human exchange outputs because they may expose local paths.

## Next Phase

Phase 18 should consume completed human decision records and define the first
real-source onboarding path that remains blocked until every required approval,
defer decision, and source identity contract is satisfied.

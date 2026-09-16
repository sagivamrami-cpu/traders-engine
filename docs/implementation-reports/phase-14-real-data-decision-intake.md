# Phase 14 Real-Data Decision Intake Report

## Scope

Phase 14 lets readiness reporting optionally merge a human-maintained decision
file so satisfied checklist items appear in the readiness report. A decision
may satisfy only a known checklist `item_id`, and only when it is `APPROVED`
and carries approver, timestamp, scope, and non-fixture evidence. The default
repository state remains `BLOCKED` because no approving decision file is
committed.

It does not approve any production data source, fetch vendor data, store raw
market data, train a production model, backtest, integrate a broker, run live
execution, deploy, or allocate capital. The Phase 12 checklist file is
unchanged.

## Files

- schemas/real_data_decisions.schema.json: decision-file contract (new)
- configs/research/real-data-decisions-template.yaml: explicitly non-approving
  template showing every required field (new)
- trading_system/research/readiness.py: decision dataclasses, loader, applier,
  and optional `decisions` input on the report builder (modified)
- schemas/real_data_readiness_report.schema.json: report version bump to
  `real-data-readiness-report-0.2.0`, required `decisions_version`
  (string or null), optional per-item `decision` payload (modified)
- tools/real_data_readiness.py: optional `--decisions` argument; no-arg
  behavior unchanged (modified)
- tools/validate_phase14.py: deterministic Phase 14 validator (new)
- tests/research/test_real_data_readiness.py: decision intake tests (modified)
- tests/research/test_phase14_validator.py: validator smoke test (new)

## Tests

- `python -m pytest tests/research/test_real_data_readiness.py -v` (17 passed)
- `python -m pytest tests/research/test_phase14_validator.py -v` (1 passed)
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`
- `python tools/validate_phase14.py`
- `python tools/real_data_readiness.py`
- `python tools/real_data_readiness.py --decisions configs/research/real-data-decisions-template.yaml`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v` (159 passed)

## Decisions

- Decision file version is `real-data-decisions-0.1.0` with entries requiring
  `item_id`, `decision`, `approver`, `decided_at`, `scope`, and a non-empty
  `evidence` list; the loader and the JSON schema both enforce this.
- `decision` values are `APPROVED` and `NOT_APPROVED`. Only `APPROVED` marks
  an item `SATISFIED`; `NOT_APPROVED` records the decision on the item but
  leaves it `OPEN_HUMAN_DECISION`.
- An explicit defer or local-only resolution (per checklist labels) is
  recorded as `APPROVED` with the defer spelled out in `scope`. Codex may
  split this into a dedicated enum value at acceptance if preferred.
- Unknown checklist item ids and duplicate item ids raise `ValueError`.
- `APPROVED` decisions whose scope or evidence mention `fixture` or
  `synthetic` (case-insensitive, path-separator-normalized) raise
  `ValueError`, so fixture and synthetic data cannot satisfy readiness.
- `decided_at` must be an ISO 8601 timestamp with an explicit UTC offset.
- The committed template contains a single `NOT_APPROVED` placeholder entry,
  so it demonstrates every required field while satisfying nothing.
- The readiness report always carries `decisions_version` (null when no
  decision file is merged) and embeds the decision payload on decided items
  for the audit trail; `report_id` hashing includes the decisions version and
  full required-item payloads, including decision evidence.

## Unresolved Risks

- No real historical CSV has been provided.
- No production OHLCV vendor or local-only source decision has been approved.
- No raw-data storage root, retention duration, or license has been approved.
- No order-flow or options source decision has been recorded.
- No human decision file exists; readiness remains `BLOCKED` end to end.

## Next Phase

A human approver can now create a decision file (modeled on the template, with
evidence linking to records under `agent-exchange/decisions/`) and pass it via
`python tools/real_data_readiness.py --decisions <path>` to see satisfied
items reflected. Until then every readiness report stays `BLOCKED`.

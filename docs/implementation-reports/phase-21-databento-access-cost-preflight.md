# Phase 21 Databento Access Cost Preflight

## Summary

Phase 21 adds a safe Databento vendor preflight for GC order-flow/options planning. It does not download market data, does not approve spending, and does not change production readiness.

## Added

- `configs/data/databento-gc-vendor-preflight.yaml`
- `schemas/databento_gc_vendor_preflight.schema.json`
- `trading_system/research/databento_vendor_preflight.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `tests/research/test_databento_vendor_preflight.py`
- `tests/research/test_phase21_validator.py`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`

## Safety Guarantees

- API key source is `ENV:DATABENTO_API_KEY`; the key value is never serialized.
- Offline mode performs no Databento import or API call.
- Online mode is limited to metadata, symbology, and `metadata.get_cost`.
- Online mode is blocked until a separate human-reviewed contract/stype decision exists.
- `timeseries.get_range`, paid downloads, and dataset construction remain blocked.
- Options parent symbol remains `UNCONFIRMED_DO_NOT_QUERY`.
- `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` remain open.

## Verification

Run:

```powershell
python -m pytest tests\research\test_databento_vendor_preflight.py -q
python -m pytest tests\research\test_phase21_validator.py -q
python tools\validate_phase21.py
```

Expected status:

- Phase 21 artifacts validated.

## Contract/Stype Gate

Groq correctly identified that `GC` as `stype_in: raw_symbol` is ambiguous for
Databento futures. Phase 21 now blocks `--online-cost-estimate` even when
`DATABENTO_API_KEY` exists unless a future contract/stype decision is supplied.

The decision template is
`configs/data/databento-gc-contract-stype-decision-template.yaml`.

It keeps these choices separate:

- dated raw symbol, for example `GCZ6`
- parent futures, for example `GC.FUT`
- continuous front month, for example `GC.v.0`

The template does not approve any data purchase and does not approve XAUUSD,
GLD, options, feature construction, training, or trading.

## Claude Code Review Intake

Claude Code reviewed Phase 21 and returned `ACCEPT_WITH_CHANGES` in
`agent-exchange/reviews/2026-08-31T233000Z-claude-code-review-phase-21-databento-access-cost-preflight.md`.

Codex implemented the review findings:

- F1: `tools/preflight_databento_gc_vendor.py` now catches top-level exceptions and emits sanitized JSON to stderr without tracebacks, local paths, or key values.
- F2: tests now cover cost estimates above `max_estimated_cost_usd`, missing schemas, and `metadata.get_cost` failures.
- F3: tests now include explicit failing guards for `batch` and `live` SDK surfaces.

Re-run:

```powershell
python -m pytest tests\research\test_databento_vendor_preflight.py tests\research\test_phase21_validator.py -q
python tools\validate_phase21.py
```

Expected status:

- 15 focused tests pass.
- Phase 21 artifacts validated.
- Real-data readiness stays `BLOCKED`.
- GC decisions stay at five satisfied and two open items.

## Groq Review Intake

Groq reviewed Phase 21 and returned `BLOCKED` in
`agent-exchange/reviews/2026-08-31T233500Z-groq-review-phase-21-databento-access-cost-preflight.md`.

Codex implemented the applicable hardening:

- Replaced `READY` report statuses with report-only `RECORDED` statuses.
- Replaced positive `AVAILABLE` metadata statuses with non-approval statuses.
- Added `contract_identity_status: UNDECLARED_PENDING_RESEARCH`.
- Added `stype_in_status: RESEARCH_DECISION_PENDING`.
- Added `estimate_window_role: SAMPLE_DAY_NOT_FULL_INTERVAL`.
- Added `coverage_status: NOT_PROVEN_SAMPLE_DAY_ONLY`.
- Added `mbo_era_status: MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION`.
- Added per-request `purchase_candidate: false`.
- Added per-request `symbol_identity_status: AMBIGUOUS_NOT_A_DATED_CONTRACT`.
- Kept request `symbols` schema-const to `["GC"]`; `GC` is only a canonical research token, not a proven Databento dated contract.
- Added tests rejecting `XAUUSD` and `GLD` policy aliases and schema payload aliases.
- Added blocked actions for order-flow/options approval, options-parent querying, MBO purchase, GC-to-XAUUSD/GLD mapping, batch submission, real dataset construction, and deployment.
- Changed MBO handling to reference-only; online mode no longer calls `metadata.get_cost` for `mbo`.
- Added a safe client wrapper that exposes only `metadata` and `symbology` and raises on `timeseries`, `batch`, and `live`.
- Blocked real online cost-estimate calls until a contract/stype decision exists.
- Enum-locked nested metadata, availability, and purpose strings in the schema.

Codex did not adopt the exact review wording `MDP2_PRE_2017_NOT_AVAILABLE`
because the current Databento documentation snapshot inspected by Codex says
GLBX.MDP3 coverage starts in June 2010. The implemented field uses the
more conservative `MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION`, which avoids
asserting either side before a live vendor coverage check.

Groq re-checked the hardening in
`agent-exchange/reviews/2026-09-01T001000Z-groq-recheck-phase-21-databento-hardening.md`
and returned `ACCEPT`, with optional low-severity recommendations. Codex
implemented the schema enum-lock and updated the stale test-count wording.

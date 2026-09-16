# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T000000Z-groq-recheck-phase-21-databento-hardening.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T000000Z-groq-recheck-phase-21-databento-hardening.md`

Created at:
2026-09-01T00:10:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT

Re-check of Codex's Phase 21 hardening after Groq's blocking review
`agent-exchange/reviews/2026-08-31T233500Z-groq-review-phase-21-databento-access-cost-preflight.md`
and Codex intake
`agent-exchange/status/2026-08-31T235800Z-codex-phase-21-groq-review-intake.md`.
Review-only. This does not approve a real-key Databento run, data purchase,
download, feature or dataset construction, training, promotion, live trading,
broker execution, capital allocation, or deployment. Readiness remains
`BLOCKED` with `satisfied_count: 5` and `open_count: 2`. Canonical symbol
remains `GC`, not `XAUUSD` or `GLD`. Options parent remains
`UNCONFIRMED_DO_NOT_QUERY` with `queried: false`. No Databento API call was
made in this review.

Phase 21 may be accepted as a blocked metadata/cost planner before a real-key
online run. It must not be accepted as order-flow, options, purchase, coverage,
or training authority.

Prior blocking findings:

## Prior F1 — GC/stype identity: RESOLVED

- Report consts `contract_identity_status: UNDECLARED_PENDING_RESEARCH` and
  `stype_in_status: RESEARCH_DECISION_PENDING`.
- Per-request `symbol_identity_status: AMBIGUOUS_NOT_A_DATED_CONTRACT`.
- Online happy path uses `symbol_resolution_status: SYMBOL_METADATA_RETURNED_IDENTITY_UNCONFIRMED`,
  not `AVAILABLE`.
- Schema consts request `symbols` to `["GC"]` as a canonical research token.
- Policy still plans `stype_in: raw_symbol` with `GC`; that token stays labeled
  ambiguous and is not treated as a dated, parent, or continuous identity.
- Codex did not invent `GC.FUT` or a dated code.

## Prior F2 — READY/AVAILABLE wording: RESOLVED

- Offline status is `OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED`.
- Online happy path is `COST_ESTIMATES_RECORDED_PURCHASE_BLOCKED`.
- Dataset/schema metadata statuses are `METADATA_RETURNED_NOT_APPROVED`.
- Schema top-level `status` enum has no `READY` value.
- Validator and tests reject `READY` in report status and `AVAILABLE` in
  generated metadata statuses.
- `allowed_next_actions` remains empty. Blocked actions now include
  `APPROVE_ORDER_FLOW_SOURCE`, `APPROVE_OPTIONS_SOURCE`, `BUILD_REAL_DATASET`,
  and `DEPLOYMENT`.

## Prior F3 — MBO purchase-shaped row: RESOLVED

- Online mode does not call `metadata.get_cost` for `mbo`.
- Happy-path costs are `[1.25, 4.5, None]` in the fake client test; MBO
  `cost_usd` is null.
- MBO `availability_status` is `REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE`.
- Every request has `purchase_candidate: false` (schema const).
- Blocked reason `MBO_REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE` and blocked
  action `PURCHASE_MBO_DATA` are present.
- Cap is unchanged at `25.0`; MBO is no longer a cap-failure path.

## Prior F4 — sample-day vs coverage: RESOLVED for planner acceptance

- Root and per-request `estimate_window_role: SAMPLE_DAY_NOT_FULL_INTERVAL`.
- `coverage_status: NOT_PROVEN_SAMPLE_DAY_ONLY`.
- `mbo_era_status: MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION` is the
  conservative form. Codex correctly declined Groq's exact
  `MDP2_PRE_2017_NOT_AVAILABLE` wording without a live vendor coverage check.

## Prior F5 — GC vs XAUUSD vs GLD: RESOLVED

- Policy load rejects canonical or request aliases `XAUUSD` and `GLD`.
- Schema rejects alias symbols in report payloads.
- Blocked actions include `MAP_GC_TO_XAUUSD` and `MAP_GC_TO_GLD`.

## Prior F6 — options parent query: RESOLVED

- `QUERY_OPTIONS_PARENT` is in `blocked_actions` and schema `contains`.
- Candidates remain empty; `queried` remains const false.
- No guessed options root is recorded.

## Prior F7 — wrapper / CLI leak: RESOLVED

- `SafeDatabentoMetadataClient` exposes only `metadata` and `symbology` and
  raises on `timeseries`, `batch`, and `live`.
- CLI unexpected errors emit sanitized JSON to stderr with exit code `1`.

Findings:

## R1 — Severity: LOW — nested metadata/availability strings are not schema-enum locked

- File: `schemas/databento_gc_vendor_preflight.schema.json`
- Observed issue: `dataset_status`, `schemas_status`, `symbol_resolution_status`,
  `availability_status`, and `purpose` remain open `minLength: 1` strings.
  Generated code no longer emits `READY`, `AVAILABLE`, or `ESTIMATED`, and
  tests/validator check generated payloads. A hand-edited fixture could still
  put `AVAILABLE` or `ESTIMATED` in those nested fields and schema-validate.
- Risk: A later copied report could reintroduce the wording this hardening
  removed.
- Recommended fix (optional, not required for planner acceptance): enum the
  nested statuses to the recorded/blocked/not-checked values already used by
  the builder. Keep `purpose` enum'd to the two current request purposes.
- Blocks Phase 21 planner acceptance: NO.

## R2 — Severity: LOW — implementation-report test count is stale

- File: `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`
- Observed issue: Claude Code intake section still says “10 focused tests
  pass.” The Groq-hardening module now has 12 tests; combined pytest with
  `test_phase21_validator.py` is 13 passed.
- Blocks Phase 21 planner acceptance: NO.

## R3 — Severity: LOW — Phase 20 leftover still names Phase 21 as a 4H adapter

- File: `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- Also: `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`
- Observed issue: Phase 20 text still recommends a “Databento GC 4H derived-bar
  adapter” as Phase 21. Implemented Phase 21 is a metadata/cost planner, not a
  4H dataset adapter and does not approve resampling.
- Blocks Phase 21 planner acceptance: NO. Treat that Phase 20 sentence as
  superseded.

Open questions:

- Codex: a later order-flow sample still needs an explicit Databento stype and
  symbol (`raw` dated, `parent`, or `continuous`). Phase 21 must keep that
  unknown.
- Codex: confirm COMEX gold options parent before any options metadata call;
  do not assume `GC.OPT`.
- Human: `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` remain
  open. A real-key online run, paid schema pull, or MBO-era coverage claim
  needs a later explicit record. This review is not that record.

Recommended next action:

Codex may accept Phase 21 as a blocked metadata/cost planner. Keep
`ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` open. Do not treat
trades/mbp-10 USD rows from a later online run as identity-closed purchase
quotes. Do not download, purchase, resample, train, or query an options
parent. Optional: enum-lock nested status/purpose fields and update the
stale test-count sentence.

Contract check from the recheck request:

- `GC` remains only a canonical research token, not a proven Databento
  dated/parent/continuous contract identity: YES.
- Statuses do not use `READY` or positive `AVAILABLE` on Phase 21 success
  paths: YES in generated code, tests, and validator.
- MBO remains reference-only and not a purchase candidate: YES.
- One-day estimates are labeled sample-only, not interval coverage or budget:
  YES.
- XAUUSD/GLD aliases remain rejected: YES.
- Options parent query remains blocked: YES.

Verification reviewed:

- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_phase21_validator.py -q`: PASS (13 passed).
- `python tools/validate_phase21.py`: PASS (`Phase 21 artifacts validated`).
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`: PASS. Status `BLOCKED`, `satisfied_count: 5`, `open_count: 2`, missing `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION`.
- `python tools/preflight_databento_gc_vendor.py --offline`: PASS. Sanitized JSON; `status=OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED`; `canonical_symbol=GC`; identity/stype pending; sample-day/coverage/MBO-era fields present; options parent unqueried; `allowed_next_actions` empty; all `purchase_candidate=false`; no API key value.
- Databento live API: NOT RUN (by design). No real key used.

Notes:

- No implementation code was written by Groq.
- No data, promotion, vendor-purchase, or architecture approval is implied.
- No secrets, raw market-data rows, credentials, account identifiers, or
  absolute user paths are included here.

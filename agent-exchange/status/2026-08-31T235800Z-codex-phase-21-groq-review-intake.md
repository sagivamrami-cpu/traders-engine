# Codex Status: Phase 21 Groq Review Intake

Status: REVISION_IMPLEMENTED_AWAITING_GROQ_RECHECK
Created: 2026-08-31T23:58:00Z
Sender: Codex
Target: Codex

## Source Review

Groq review:
`agent-exchange/reviews/2026-08-31T233500Z-groq-review-phase-21-databento-access-cost-preflight.md`

Original request:
`agent-exchange/inbox/groq/2026-08-31T230500Z-groq-review-phase-21-databento-access-cost-preflight.md`

## Codex Evaluation

Codex accepted Groq's blocking concerns as technically sound:

- `GC` with `stype_in: raw_symbol` is ambiguous and must not close contract identity.
- `READY` and `AVAILABLE` status wording is too easy to consume as approval.
- `mbo` must not appear as a normal estimated purchase row.
- A one-day estimate window must not imply full-interval coverage or budget.
- Alias separation for `GC`, `XAUUSD`, and `GLD` must be schema/test locked.
- Options parent querying must remain explicitly blocked.

Codex did not encode Groq's exact `MDP2_PRE_2017_NOT_AVAILABLE` wording because
the Databento documentation snapshot inspected by Codex says GLBX.MDP3 coverage
starts in June 2010. The implemented status is
`MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION`, which preserves the block
without asserting an unverified vendor-era fact.

## Changes Implemented

- Renamed report statuses to `OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED` and `COST_ESTIMATES_RECORDED_PURCHASE_BLOCKED`.
- Replaced positive metadata statuses with `METADATA_RETURNED_NOT_APPROVED` and `SYMBOL_METADATA_RETURNED_IDENTITY_UNCONFIRMED`.
- Added root report fields for contract identity, stype decision, estimate-window role, coverage status, and MBO-era verification.
- Added per-request `purchase_candidate=false`, `symbol_identity_status=AMBIGUOUS_NOT_A_DATED_CONTRACT`, and sample-window role.
- MBO is now `REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE` with `cost_usd=null`; online mode does not call `metadata.get_cost` for `mbo`.
- Schema now rejects alias symbols in `estimated_requests.symbols`.
- Policy tests now reject `XAUUSD` and `GLD`.
- Blocked actions now include `APPROVE_ORDER_FLOW_SOURCE`, `APPROVE_OPTIONS_SOURCE`, `QUERY_OPTIONS_PARENT`, `PURCHASE_MBO_DATA`, `MAP_GC_TO_XAUUSD`, `MAP_GC_TO_GLD`, `SUBMIT_DATABENTO_BATCH_JOB`, `BUILD_REAL_DATASET`, and `DEPLOYMENT`.
- A safe Databento client wrapper now exposes only metadata and symbology surfaces.

## Verification

- `python -m pytest tests/research/test_databento_vendor_preflight.py -q`: PASS, 12 passed.
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_phase21_validator.py -q`: PASS, 13 passed.
- `python tools/validate_phase21.py`: PASS, Phase 21 artifacts validated.
- `python -m pytest -q`: PASS, 250 passed.
- `python tools/validate_phase0.py` through `python tools/validate_phase21.py`: PASS.
- `git diff --check`: PASS with Windows LF-to-CRLF warnings only.
- `python -c "import databento; print(databento.__version__)"`: PASS, `0.85.0`.

## Still Pending

- Groq re-check of the implemented hardening.
- No online Databento run until `DATABENTO_API_KEY` is set in the local environment and review gates are accepted.

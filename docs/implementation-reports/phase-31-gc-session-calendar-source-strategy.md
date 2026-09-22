# Phase 31 GC Session Calendar Source Strategy Implementation Report

## Summary

Implemented the D2-approved GC session-calendar source strategy as a fail-closed policy artifact plus a sanitized observed-activity profiling tool. D2 approves the evidence strategy only; it does not authorize session-calendar registration, Databento API queries, real resampling, dataset construction, feature building, label building, or model training.

## Files

- `agent-exchange/decisions/2026-09-01T185500Z-human-d2-session-calendar-source-strategy-v1.md`
- `configs/data/gc-session-calendar-source-strategy.yaml`
- `schemas/gc_session_calendar_source_strategy.schema.json`
- `schemas/gc_observed_activity_calendar_profile.schema.json`
- `trading_system/research/gc_session_calendar_source_strategy.py`
- `tools/validate_gc_session_calendar_source_strategy.py`
- `tools/inspect_gc_observed_activity_calendar.py`
- `tools/validate_phase31.py`
- `tests/research/test_gc_session_calendar_source_strategy.py`
- `tests/research/test_phase31_validator.py`

## D2 Decision

- Decision: `APPROVED_SOURCE_STRATEGY_V1_NOT_CALENDAR_AUTHORIZATION`
- Observed activity from the already-licensed GC 1s archive is the first zero-cost evidence leg.
- Official CME GC/Globex documents are the required authoritative public reference.
- Databento `status` schema remains blocked pending separate cost/source/query approval.
- TradingView is non-authoritative and may be used only for informal visual sanity checks.
- Every calendar era must be evidence-backed; unverifiable eras remain `UNVERIFIED_HISTORICAL`.
- Scheduled closures and observed data/venue gaps must be separated and reconciled explicitly.

## Fail-Closed Guards

- `calendar_registration_allowed=false`
- `databento_status_leg.query_allowed=false`
- `session_calendar_gate_status=UNSATISFIED_SOURCE_STRATEGY_ONLY`
- observed-activity profiles emit `UNSATISFIED_OBSERVED_ACTIVITY_ONLY`
- `REGISTER_SESSION_CALENDAR`, `QUERY_DATABENTO_STATUS_SCHEMA`, `RESAMPLE_REAL_BARS`, `BUILD_REAL_DATASET`, and `TRAIN_PRODUCTION_MODEL` remain blocked.
- Phase 1 rejects `cme-globex-metals-research-pending-v1` in `configs/data/session-calendar.yaml` until a future full calendar implementation decision exists.
- Phase 31 validator also rejects `cme-globex-metals-research-pending-v1` in `configs/data/session-calendar.yaml`, closing the direct D2 registration-bypass review finding.

## Real Archive Smoke Check

The local GC 1s archive was inspected read-only with a three-member sample. Sanitized aggregate output:

- status: `OBSERVED_ACTIVITY_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED`
- parquet entries: `195`
- total row count from metadata: `104212803`
- sampled entries: `3`
- observed sampled span: `2010-06-07T00:00:02Z` to `2026-08-05T23:59:49Z`
- session calendar remains unsatisfied.
- no local absolute path or raw market rows were emitted.

## Verification

- `python -m pytest tests\research\test_gc_session_calendar_source_strategy.py -q`: PASS, 5 passed.
- `python -m pytest tests\research\test_phase31_validator.py -q`: PASS, 1 passed.
- `python tools\validate_phase31.py`: PASS, `Phase 31 artifacts validated`.

## Review Intake

- Claude Code Phase 31: `ACCEPT_WITH_CHANGES`.
- M1 implemented: `tools/validate_phase31.py` now directly checks `configs/data/session-calendar.yaml` and fails closed if the pending GC metals calendar id is registered before D2 calendar implementation.
- L1 noted: Groq is unavailable due to weekly quota; route a retrospective Groq review when quota is available again.

## Post-Review Verification

- `python -m pytest tests\research\test_gc_session_calendar_source_strategy.py tests\research\test_phase31_validator.py -q`: PASS, 7 passed.
- `python tools\validate_phase1.py`: PASS, `Phase 1 artifacts validated`.
- `python tools\validate_phase24.py`: PASS, `Phase 24 artifacts validated`.
- `python tools\validate_phase28.py`: PASS, `Phase 28 artifacts validated`.
- `python tools\validate_phase31.py`: PASS, `Phase 31 artifacts validated`.

## Remaining Blockers

- Full era-versioned CME Globex metals session calendar is not implemented.
- Databento `status` schema query is not approved.
- Holiday/maintenance/DST overlay is not implemented.
- Scheduled-vs-observed discrepancy handling is not implemented.
- Missing-bar policy remains unsatisfied.
- Dataset construction remains blocked.
- Training remains blocked.

## Next

Implement the full D2 calendar-construction policy candidate from observed-activity aggregates and official CME references, then route it to Claude Code for review before any calendar registration.

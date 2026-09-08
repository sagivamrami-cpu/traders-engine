# Phase 32 GC Session Calendar Construction Policy Implementation Report

## Summary

Implemented a fail-closed GC session-calendar construction policy candidate. This phase converts the D2-approved source strategy into an explicit construction policy: what the future full calendar must prove, which evidence legs are required, and which actions remain blocked until the calendar is actually implemented and reviewed.

This phase does not register a GC calendar, query Databento, resample real bars, build a dataset, build labels, or train a model.

## Files

- `configs/data/gc-session-calendar-construction-policy.yaml`
- `schemas/gc_session_calendar_construction_policy.schema.json`
- `trading_system/research/gc_session_calendar_construction_policy.py`
- `tools/validate_gc_session_calendar_construction_policy.py`
- `tools/validate_phase32.py`
- `tests/research/test_gc_session_calendar_construction_policy.py`
- `tests/research/test_phase32_validator.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `tools/validate_phase24.py`

## Policy Shape

- Calendar id remains `cme-globex-metals-research-pending-v1`.
- Normal-session template is documented in Chicago time for GC Globex research.
- Era-versioned evidence is required before any calendar membership can be trusted.
- Holiday, special-hours, maintenance, DST, and venue-halt overlays are required.
- Scheduled-vs-observed reconciliation and source attribution are required.
- 30m UTC bar membership rules are explicitly marked `REQUIRED_NOT_IMPLEMENTED`.

## Fail-Closed Guards

- `calendar_registration_allowed=false`
- `construction_allowed=false`
- `dataset_construction_allowed=false`
- `resampling_allowed=false`
- `training_allowed=false`
- `SESSION_CALENDAR` remains in the real dataset contract's unsatisfied gates.
- `REGISTER_SESSION_CALENDAR`, `QUERY_DATABENTO_STATUS_SCHEMA`, `RESAMPLE_REAL_BARS`, `BUILD_REAL_DATASET`, and `TRAIN_PRODUCTION_MODEL` remain blocked.

## Verification

- `python -m pytest tests\research\test_gc_session_calendar_construction_policy.py tests\research\test_phase32_validator.py -q`: PASS, 3 passed.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py -q`: PASS, 5 passed.
- `python tools\validate_phase24.py`: PASS, `Phase 24 artifacts validated`.

## Review Intake

- Claude Code Phase 32: `ACCEPT_WITH_CHANGES`.
- M1 implemented: Phase 32 now directly tests that `cme-globex-metals-research-pending-v1` is absent from `configs/data/session-calendar.yaml` and rejects premature registration.
- L1 implemented: the normal-session template now carries `template_status=TEMPLATE_ONLY_NOT_ERA_EVIDENCE`.
- L2 noted: Groq is unavailable due to weekly quota; queue a retrospective Groq review when quota resets.

## Post-Review Verification

- `python -m pytest tests\research\test_gc_session_calendar_construction_policy.py tests\research\test_phase32_validator.py -q`: PASS, 5 passed.
- `python tools\validate_phase32.py`: PASS, `Phase 32 artifacts validated`.

## Remaining Blockers

- Full authoritative CME GC/Globex historical calendar evidence has not been collected.
- Databento `status` schema query remains unapproved.
- Calendar overlay table is not implemented.
- Session membership validator is not implemented.
- Missing-bar policy remains unsatisfied.
- Real dataset construction remains blocked.
- Model training remains blocked.

## Next

Route Phase 32 to Claude Code for review. If accepted, the next technical step is an evidence-manifest/calendar-overlay design that can support a future explicit human decision to register the GC session calendar.

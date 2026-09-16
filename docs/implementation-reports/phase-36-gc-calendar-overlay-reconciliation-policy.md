# Phase 36 GC Calendar Overlay/Reconciliation Policy Implementation Report

## Summary

Implemented a fail-closed overlay/reconciliation policy candidate for the future GC session calendar. This policy connects the D2 source strategy, construction policy, CME evidence manifest, observed full aggregate, and fine observed-gap profile into one explicit gate for the future overlay table and scheduled-vs-observed reconciliation.

This phase does not implement the overlay table, register a calendar, resample real bars, build a dataset, build labels, or train a model.

## Files

- `configs/data/gc-session-calendar-overlay-reconciliation-policy.yaml`
- `schemas/gc_calendar_overlay_reconciliation_policy.schema.json`
- `trading_system/research/gc_calendar_overlay_reconciliation_policy.py`
- `tools/validate_gc_calendar_overlay_reconciliation_policy.py`
- `tools/validate_phase36.py`
- `tests/research/test_gc_calendar_overlay_reconciliation_policy.py`
- `tests/research/test_phase36_validator.py`

## Policy Shape

- Required overlay types: holiday, special hours, maintenance break, DST transition, and venue halt.
- Required reconciliation controls: source attribution, scheduled-vs-observed separation, disagreement reason code, human review for unexplained gaps, and content hash/capture manifest.
- Fine observed-gap profile is recorded as `BOUNDED_SMOKE_ONLY_FULL_PROFILE_PENDING`.
- Overlay table and reconciliation table are explicitly `REQUIRED_NOT_IMPLEMENTED`.

## Fail-Closed Guards

- `session_calendar_gate_status=UNSATISFIED_OVERLAY_RECONCILIATION_POLICY_ONLY`
- `calendar_registration_allowed=false`
- `dataset_construction_allowed=false`
- `resampling_allowed=false`
- `training_allowed=false`
- `USE_OBSERVED_GAPS_AS_SCHEDULE_AUTHORITY` is blocked.

## Verification

- `python -m pytest tests\research\test_gc_calendar_overlay_reconciliation_policy.py tests\research\test_phase36_validator.py -q`: PASS, 3 passed.
- `python tools\validate_phase36.py`: PASS, `Phase 36 artifacts validated`.

## Remaining Blockers

- Overlay table is not implemented.
- Reconciliation table is not implemented.
- Full fine observed-gap profile remains pending.
- Historical CME era evidence remains incomplete.
- Session-calendar registration remains blocked.
- Dataset construction and model training remain blocked.

## Next

Route Phase 36 to Claude Code for review. If accepted, decide whether to optimize full fine-gap scanning or proceed to dataset identity/canonical input gates while calendar remains unsatisfied.

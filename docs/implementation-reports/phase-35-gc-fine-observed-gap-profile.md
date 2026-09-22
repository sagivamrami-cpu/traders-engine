# Phase 35 GC Fine Observed Gap Profile Implementation Report

## Summary

Implemented a fine-grained observed-gap profiler for GC 1s parquet archives. The tool reads only the `ts_event` timestamp column, computes non-consecutive timestamp gaps, and emits sanitized aggregate gap summaries.

This phase does not read price/volume columns, authorize calendar membership, register a calendar, resample real bars, build a dataset, build labels, or train a model.

## Files

- `schemas/gc_fine_observed_gap_profile.schema.json`
- `trading_system/research/gc_fine_observed_gap_profile.py`
- `tools/inspect_gc_fine_observed_gap_profile.py`
- `tools/validate_phase35.py`
- `tests/research/test_gc_fine_observed_gap_profile.py`
- `tests/research/test_phase35_validator.py`

## Real Archive Checks

- Full archive attempt: started read-only over timestamp columns, then stopped because it did not complete in a practical window.
- Bounded smoke check: inspected the first `3` parquet members with `--max-members 3`.
- Smoke row count: `948007`.
- Smoke largest gap: `179104` seconds.
- Smoke non-consecutive transition count: `559329`.
- Output did not include local absolute paths, secrets, prices, volumes, labels, or raw market rows.

## Fail-Closed Guards

- `timestamp_column_only=true`
- `local_path=LOCAL_PATH_REDACTED`
- `session_calendar_gate_status=UNSATISFIED_OBSERVED_GAP_PROFILE_ONLY`
- `calendar_registration_allowed=false`
- `dataset_construction_allowed=false`
- `resampling_allowed=false`
- `training_allowed=false`

## Verification

- `python -m pytest tests\research\test_gc_fine_observed_gap_profile.py -q`: PASS, 3 passed.
- `python tools\validate_phase35.py`: PASS, `Phase 35 artifacts validated`.
- Bounded real archive smoke command with `--max-members 3`: PASS.

## Remaining Blockers

- The full archive fine-gap profile has not completed.
- Observed gaps are not calendar authority by themselves.
- Official scheduled-vs-observed reconciliation is not implemented.
- Era-versioned overlays remain missing.
- Session-calendar registration remains blocked.
- Dataset construction and model training remain blocked.

## Next

Route Phase 35 to Claude Code for review. If accepted, improve the full-run strategy for timestamp-only gap profiling or proceed to an overlay/reconciliation policy that treats this profile as supporting evidence only.

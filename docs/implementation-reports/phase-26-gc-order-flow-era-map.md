# Phase 26 GC Order Flow Era Map Implementation Report

## Summary

Implemented a sanitized GC order-flow Parquet file catalog. Phase 26 scans every Parquet file in the order-flow archive, records file role, columns, timestamp column, timezone status, row count, start/end timestamps, CVD presence, and file-range overlap with the known 2017 damaged-aggressor window.

This phase does not approve order-flow source readiness, build order-flow features, build a real dataset, create labels, train a model, query vendors, extract archives, promote models, deploy, live trade, execute broker actions, or allocate capital.

## Files

- `docs/superpowers/plans/2026-09-01-phase-26-gc-order-flow-era-map.md`
- `schemas/gc_order_flow_era_map.schema.json`
- `trading_system/research/gc_order_flow_era_map.py`
- `tools/inspect_gc_order_flow_era_map.py`
- `tools/validate_phase26.py`
- `tests/research/test_gc_order_flow_era_map.py`
- `tests/research/test_phase26_validator.py`

## Real Archive Smoke Check

Sanitized profile of the supplied local order-flow ZIP returned:

- status: `ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED`
- parquet eras: `5`
- roles: `ORDER_FLOW_1M:3`, `OHLCV_1M:2`
- `order_flow_era_map_gate_status=UNSATISFIED_FILE_CATALOG_ONLY`
- `training_allowed=false`
- `dataset_construction_allowed=false`
- output contained no local absolute archive path

## Gates Preserved

- `ORDER_FLOW_SOURCE_DECISION` remains `OPEN_HUMAN_DECISION`.
- Dataset construction remains blocked.
- Training remains blocked.
- The 2017 damaged-aggressor window uses half-open UTC `[start, end)` semantics.
- File-level overlap is not a row-level exclusion mask and does not satisfy the full era-map policy.
- Archived `cvd` columns are marked precomputed/unsafe and blocked from use.
- CVD remains blocked pending PIT, fold-local, era-gapped recomputation policy.
- Canonical order-flow and OHLCV inputs remain undeclared.

## Verification

- `python -m pytest tests\research\test_gc_order_flow_era_map.py tests\research\test_phase26_validator.py -q`: PASS, 5 passed.
- `python tools\validate_phase26.py`: PASS, `Phase 26 artifacts validated`.
- Real local archive smoke check: PASS, 5 Parquet eras, no local path in sanitized payload.

## Review Fixes

- Claude Code Phase 26 M1: fixed damaged-window overlap for files whose last observation is exactly at the damaged-window start. Per-file era ranges are first/last observation ranges, so overlap now treats the era end as inclusive against the half-open damaged window.
- Added boundary test: `test_gc_order_flow_era_map_marks_file_ending_at_damaged_start_as_overlap`.
- Groq Phase 26 F1: renamed the status to `ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED` and kept `ORDER_FLOW_ERA_MAP` unsatisfied.
- Groq Phase 26 F2/F3: added cumulative-feature status, raw-tick era status, precomputed-CVD status, and `file_range_overlaps_known_damage`.
- Groq Phase 26 F5: expanded blocked actions to include Phase 24 denials for CVD, macro, options, 4H CSV, HHLL, and GC alias mapping.

## Next

Request Claude Code and Groq review of the hardened catalog. A later phase must design the real availability/era policy and row-level masks; this catalog must not close `ORDER_FLOW_ERA_MAP`.

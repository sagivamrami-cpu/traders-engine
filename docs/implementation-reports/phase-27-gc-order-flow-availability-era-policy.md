# Phase 27 GC Order Flow Availability Era Policy Implementation Report

## Summary

Implemented a sanitized GC order-flow availability-era policy candidate. Phase 27 consumes the Phase 26 Parquet file catalog, splits each file range around the known 2017 damaged-aggressor window, records cumulative reset requirements, and keeps all feature, dataset, and training actions blocked.

This phase does not approve `ORDER_FLOW_SOURCE_DECISION`, does not satisfy `ORDER_FLOW_ERA_MAP`, does not implement row-level masks, does not build features, does not build a real dataset, does not create labels, does not train a model, does not query vendors, and does not expose local paths or raw market rows.

## Files

- `docs/superpowers/plans/2026-09-01-phase-27-gc-order-flow-availability-era-policy.md`
- `schemas/gc_order_flow_availability_era_policy.schema.json`
- `trading_system/research/gc_order_flow_availability_era_policy.py`
- `tools/inspect_gc_order_flow_availability_era_policy.py`
- `tools/validate_phase27.py`
- `tests/research/test_gc_order_flow_availability_era_policy.py`
- `tests/research/test_phase27_validator.py`

## Policy Behavior

- `status=FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED`
- `policy_applies_to=UNSELECTED_ZIP_MEMBERS`
- `order_flow_era_map_gate_status=UNSATISFIED_POLICY_CANDIDATE_ONLY`
- every per-file policy has `allowed_for_training=false`
- every regime is a half-open UTC annotation only, not a row-level mask
- OHLCV files are not subjected to the order-flow aggressor-damage window without a separate decision
- archived `cvd` remains `PRECOMPUTED_CUMULATIVE_UNSAFE`
- cumulative carry is reset-required at file start, known damage boundaries, and walk-forward fold boundaries
- `ROW_LEVEL_2017_MASK`, canonical input decisions, cumulative feature policy, order-flow source decision, and dataset construction authorization remain required

## Real Archive Smoke Check

Sanitized inspection of the supplied local order-flow archive returned:

- status: `FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED`
- Parquet file policies: `5`
- `training_allowed=false`
- `dataset_construction_allowed=false`
- gate status: `UNSATISFIED_POLICY_CANDIDATE_ONLY`
- output contained no local absolute archive path

## Verification

- `python -m pytest tests\research\test_gc_order_flow_availability_era_policy.py tests\research\test_phase27_validator.py -q`: PASS, 5 passed.
- `python tools\validate_phase27.py`: PASS, `Phase 27 artifacts validated`.
- Real local archive smoke check: PASS, 5 file policies, source-blocked, no local path in sanitized output.

## Review Fixes

- Claude Code Phase 27: accepted as a blocked policy candidate.
- Groq Phase 27 F1: added `ORDER_FLOW_ERA_MAP` to remaining gates and changed the status token to `FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED`.
- Groq Phase 27 F2: added per-regime `semantics=HALF_OPEN_UTC_ANNOTATION_ONLY_NOT_ROW_MASK` and kept `ROW_LEVEL_2017_MASK` unsatisfied.
- Groq Phase 27 F3: stopped applying the order-flow aggressor damage split to `OHLCV_1M` files.
- Groq Phase 27 F4/F5: added `policy_applies_to=UNSELECTED_ZIP_MEMBERS` and unioned the Phase 24 denial set into blocked actions.

## Remaining Blockers

- `ORDER_FLOW_SOURCE_DECISION`
- `CANONICAL_ORDER_FLOW_INPUT`
- `CANONICAL_OHLCV_INPUT`
- `ROW_LEVEL_2017_MASK`
- `CUMULATIVE_FEATURE_POLICY`
- `SESSION_CALENDAR`
- `BAR_BOUNDARY`
- `TIMESTAMP_ROLE`
- `AVAILABLE_AT_POLICY`
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `DATASET_IDENTITY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`

## Next

Phase 27 is accepted only as a blocked file-range policy candidate. It must not close `ORDER_FLOW_ERA_MAP`; the next implementation work should focus on label contract and split/embargo policy candidates or on Phase 28 review intake.

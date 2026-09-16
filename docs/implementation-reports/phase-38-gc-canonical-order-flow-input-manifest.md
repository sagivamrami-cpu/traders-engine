# Phase 38 - GC Canonical Order-Flow Input Manifest

## Outcome

Phase 38 records the supplied Databento GC order-flow archive as a canonical
order-flow input identity, without authorizing source use, feature construction,
dataset construction, or training.

The selected member is `gc/GCext_of_1m.parquet` because it provides the longest
available one-minute `volume`, `delta`, and `trades` history and avoids treating
archived `cvd` as an ingestible cumulative feature.

## Recorded Input

- Archive hash: `34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155`
- Archive size: `2496805183`
- Archive members: `30`
- Parquet members: `5`
- Selected order-flow member: `gc/GCext_of_1m.parquet`
- Selected member columns: `volume`, `delta`, `trades`, `minute`
- Selected member rows: `5388775`
- Observed span: `2011-01-02T23:00:00Z` to `2026-07-17T20:59:00Z`

## Safety Boundaries

- `ORDER_FLOW_SOURCE_DECISION` remains open.
- The known damaged aggressor-side window remains excluded:
  `2017-01-01T00:00:00Z` to `2017-06-01T00:00:00Z`.
- Archived `cvd` remains forbidden for ingestion.
- `ORDER_FLOW_ERA_MAP` remains unsatisfied until row-level masks and cumulative
  reset policy are implemented.
- `dataset_construction_allowed` remains `false`.
- `training_allowed` remains `false`.

## Verification

- `python -m pytest tests\research\test_gc_canonical_order_flow_input_manifest.py -q`
  PASS, 2 passed.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py -q`
  PASS, 5 passed.
- `python -m pytest tests\research\test_gc_pretraining_readiness.py -q`
  PASS, 4 passed.
- `python -m pytest tests\research\test_phase38_validator.py -q`
  PASS, 1 passed.
- `python tools\validate_phase38.py`
  PASS, `Phase 38 artifacts validated`.
- `python tools\gc_pretraining_readiness.py ...`
  PASS; `CANONICAL_ORDER_FLOW_INPUT` no longer appears in
  `required_pretraining_gates`.

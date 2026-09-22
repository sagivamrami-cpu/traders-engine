# Phase 39 - GC Order-Flow Row Mask and Cumulative Policy

## Outcome

Phase 39 records the v1 order-flow row-mask and cumulative-feature policy for
the canonical GC order-flow input. It is a policy and guard implementation only;
it does not build order-flow features, construct a dataset, or train a model.

## Row Mask

The known damaged aggressor-side window is excluded with half-open UTC
semantics:

- Excluded start: `2017-01-01T00:00:00Z`
- Excluded end: `2017-06-01T00:00:00Z`
- Predicate: `minute < damaged_start OR minute >= damaged_end`

This keeps the boundary minute at `2017-01-01T00:00:00Z` excluded and the
boundary minute at `2017-06-01T00:00:00Z` included again.

Naive `minute` timestamps are localized as UTC wall-clock, matching the
D3-approved timestamp policy and the canonical order-flow input manifest.

## Cumulative Policy

For v1, archived cumulative fields are not ingestible. The allowed order-flow
feature columns are:

- `volume`
- `delta`
- `trades`

The forbidden order-flow feature columns are:

- `cvd`
- `cumulative_delta`

This satisfies the cumulative-feature gate only by avoiding cumulative carry in
v1. Any future CVD or cumulative-delta feature requires a new policy version and
PIT/fold-local recomputation rules.

## Readiness Delta

`ORDER_FLOW_ERA_MAP` and `CUMULATIVE_FEATURE_POLICY` are removed from the
dataset contract's `required_unsatisfied_gates`.

The following remain blocked:

- `ORDER_FLOW_SOURCE_DECISION`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
- `REAL_DATASET_NOT_BUILT`
- all non-order-flow gates still listed by readiness

## Verification

- `python -m pytest tests\research\test_gc_order_flow_row_mask_cumulative_policy.py tests\research\test_phase39_validator.py -q`
  PASS, 5 passed.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
  PASS, 9 passed.
- `python tools\validate_phase39.py`
  PASS, `Phase 39 artifacts validated`.

## Safety

- No raw market rows were written to the repository or `agent-exchange/`.
- No local absolute paths, secrets, API keys, broker data, or account data were
  written to `agent-exchange/`.
- No dataset was built.
- No model was trained.
- No commit or push was performed.

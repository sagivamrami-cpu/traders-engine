# Phase 46-47 GC Real Dataset Build And Training Start

## Summary

Phase 46 and Phase 47 close the gap between the approved GC 30m dataset contract
and the first trainable research dataset.

Phase 46 validates the built real dataset manifest and the local rows parquet.
Phase 47 validates that pre-training readiness is `READY` for the `order_flow`
variant and that the research-only majority baseline training run is recorded.

## Implemented

- Added `tools/validate_phase46.py`.
- Added `tools/validate_phase47.py`.
- Validated `configs/datasets/gc-30m-real-dataset-build-manifest.json`.
- Validated `market-data/gc-30m-real/f9d3c1b0d02da255/rows.parquet` against:
  - manifest `rows_sha256`
  - manifest `rows_count`
  - manifest `rows_columns`
- Validated GC pretraining readiness with the built manifest.
- Validated `configs/models/gc-majority-baseline-training-run.json`.

## Dataset Lock

- dataset_id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- rows_count: `380362`
- order_flow included rows: `341056`
- order_flow train rows: `238398`
- order_flow validation rows: `45074`
- order_flow test rows: `57584`
- class distribution:
  - EXPIRED: `47922`
  - STOP_FIRST: `146567`
  - TARGET_FIRST: `146567`

## Baseline Lock

- model_type: `MAJORITY_CLASS_BASELINE`
- baseline_class: `STOP_FIRST`
- validation_accuracy: `0.4223499134756179`
- test_accuracy: `0.4404522089469297`
- promotion_allowed: `false`

## Safety Boundary

- The built dataset authorizes training start only.
- Model promotion remains blocked.
- Live trading remains blocked.
- Broker execution remains blocked.
- Capital allocation remains blocked.
- No local machine paths are allowed in the published manifests.
- No commit or push was performed.

## Verification

- `python -m pytest tests\research\test_phase46_validator.py tests\research\test_phase47_validator.py -q`: PASS, `2 passed in 34.00s`.
- `python tools\validate_phase46.py`: PASS, `Phase 46 artifacts validated`.
- `python tools\validate_phase47.py`: PASS, `Phase 47 artifacts validated`.

## Next Phase

Phase 48 can start the first real predictive model. The baseline is not an edge
claim; it is the reference line that any real model must beat out-of-sample.

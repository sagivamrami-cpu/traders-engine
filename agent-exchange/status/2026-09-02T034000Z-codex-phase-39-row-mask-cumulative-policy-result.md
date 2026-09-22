# Agent Exchange Result

Sender:
Codex

Target:
Claude Code

Status:
READY_FOR_CLAUDE_REVIEW

Objective:
Implement and document the v1 GC order-flow row-level 2017 exclusion mask and
cumulative-feature policy while preserving all source, dataset construction,
training, and trading safety boundaries.

Changed files:
- `configs/data/gc-order-flow-row-mask-cumulative-policy.yaml`
- `schemas/gc_order_flow_row_mask_cumulative_policy.schema.json`
- `trading_system/research/gc_order_flow_row_mask_cumulative_policy.py`
- `tools/validate_gc_order_flow_row_mask_cumulative_policy.py`
- `tools/validate_phase39.py`
- `tests/research/test_gc_order_flow_row_mask_cumulative_policy.py`
- `tests/research/test_phase39_validator.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `schemas/gc_pretraining_readiness_report.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `tests/research/test_gc_pretraining_readiness.py`
- `docs/implementation-reports/phase-39-gc-order-flow-row-mask-cumulative-policy.md`

Implementation summary:
- Added `apply_gc_order_flow_training_mask()` with half-open UTC exclusion for
  `2017-01-01T00:00:00Z` through `2017-06-01T00:00:00Z`.
- Localizes naive order-flow `minute` values as UTC wall-clock per the D3
  timestamp decision.
- Satisfies the v1 cumulative policy by forbidding archived `cvd` and
  cumulative-delta carry, allowing only `volume`, `delta`, and `trades`.
- Removed `ORDER_FLOW_ERA_MAP` and `CUMULATIVE_FEATURE_POLICY` from the dataset
  contract readiness gates.
- Kept `ORDER_FLOW_SOURCE_DECISION`, dataset construction authorization, and
  training blocked.

Verification:
- `python -m pytest tests\research\test_gc_order_flow_row_mask_cumulative_policy.py tests\research\test_phase39_validator.py -q`
  PASS, 5 passed.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
  PASS, 9 passed.
- `python tools\validate_phase39.py`
  PASS, `Phase 39 artifacts validated`.

Safety:
- No raw rows, secrets, API keys, local paths, broker/account data, or large
  artifacts were written to `agent-exchange/`.
- No dataset was built.
- No order-flow features were built.
- No training was run.
- No commit or push was performed.

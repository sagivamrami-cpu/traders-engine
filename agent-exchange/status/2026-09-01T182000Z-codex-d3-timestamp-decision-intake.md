# Codex Status

Status:
ACCEPTED_BY_CODEX

Subject:
D3 timestamp policy human decision intake

Decision:
`agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md`

Applied to:
- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_bar_session_timestamp_policy.schema.json`
- `schemas/gc_real_dataset_contract.schema.json`
- Phase 28 tests and validator
- GC real dataset contract tests

Effect:
- `TIMESTAMP_ROLE` is no longer an unsatisfied gate in the GC dataset contract.
- OHLCV `ts_event` is approved as 1-second interval start for v1.
- Order-flow `minute` is approved as 1-minute interval start for v1.
- Naive long-series order-flow timestamps are approved for UTC wall-clock localization for v1.

Non-effect:
- Does not approve `BAR_BOUNDARY`.
- Does not approve `SESSION_CALENDAR`.
- Does not approve `AVAILABLE_AT_POLICY`.
- Does not approve `MISSING_BAR_POLICY`.
- Does not approve order-flow/OHLCV joins.
- Does not approve resampling.
- Does not approve dataset construction.
- Does not approve label building.
- Does not approve training.

Verification:
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_phase28_validator.py -q`: PASS, 4 passed.
- `python -m pytest tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`: PASS, 9 passed.
- `python tools\validate_phase24.py`: PASS, `Phase 24 artifacts validated`.
- `python tools\validate_phase28.py`: PASS, `Phase 28 artifacts validated`.
- `python tools\validate_phase29.py`: PASS, `Phase 29 artifacts validated`.
- `python tools\validate_phase30.py`: PASS, `Phase 30 artifacts validated`.

Commit/push:
Not performed by user instruction.

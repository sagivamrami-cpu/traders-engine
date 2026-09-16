# Task 6 Report: Label Contracts

## Status

Completed inline after the Task 6 subagent hit the usage limit.

## Files Changed

- Created `configs/contracts/label-contracts.yaml`
- Updated `tests/specification/test_phase0_configs.py`

No files under `engine/`, `brand.py`, `run_daily.py`, Notion delivery, or
Telegram delivery were changed.

## TDD Evidence

### RED

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_label_contracts_define_candidate_snapshot_and_ambiguous_policy -v
```

Result: failed because
`configs/contracts/label-contracts.yaml` did not exist.

### GREEN

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_label_contracts_define_candidate_snapshot_and_ambiguous_policy -v
```

Result: 1 passed.

## Verification

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py -v
```

Result: 4 passed.

`git diff --check` exited 0. Pytest still emits the pre-existing
`pytest_asyncio` deprecation warning.

## Decisions

- Kept label horizon as `MAX_BARS_OPEN_RESEARCH_PARAMETER`; no numeric expiry
  threshold was invented.
- Kept same-bar target/stop handling as
  `AMBIGUOUS_EXCLUDED_FROM_TRAINING`.
- Referenced cost/fill policy files that are created in Task 7.

## Self-Review

- Confirmed the candidate snapshot granularity matches the implementation plan.
- Confirmed rejected candidates are explicitly required to be logged.
- Confirmed ambiguous labels are represented and excluded from training until
  a conservative policy is approved.
- Confirmed no `.superpowers/` files are tracked.

## Concerns

- The Task 6 subagent left the test-file edit in the working tree before
  hitting usage limits; the inline continuation used that existing RED test
  instead of recreating it.

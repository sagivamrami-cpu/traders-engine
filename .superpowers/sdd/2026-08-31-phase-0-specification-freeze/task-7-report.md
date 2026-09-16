# Task 7 Report: Operational Policy Skeletons

## Status

Completed inline because subagent execution is unavailable due usage limits.

## Files Changed

- Created `configs/features/feature-dependency-graph.yaml`
- Created `configs/features/freshness-policy.yaml`
- Created `configs/graphs/critical-dependency-matrix.yaml`
- Created `configs/history/historical-match-policy.yaml`
- Created `configs/decision/conflict-policy.yaml`
- Created `configs/risk/portfolio-sizing-policy.yaml`
- Created `configs/execution/cost-fill-policy.yaml`
- Created `configs/runtime/degraded-mode-policy.yaml`
- Created `configs/runtime/kill-switch-policy.yaml`
- Created `research/priority-register.yaml`
- Created `research/experiment-ledger/README.md`
- Updated `tests/specification/test_phase0_configs.py`

## TDD Evidence

### RED

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_phase0_required_policy_files_exist tests/specification/test_phase0_configs.py::test_priority_register_keeps_research_parameters_open -v
```

Result: 2 failed because the required Phase 0 policy/research files were
missing.

### GREEN

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py -v
```

Result: 6 passed.

## Decisions

- Used `OPEN_RESEARCH` for compute, TTL, timeframe, session, source latency,
  and market-status values that require evidence.
- Used `OPEN_HUMAN_DECISION` for the default sizing family.
- Preserved `TWO_OUT_OF_THREE_VOTE` as a forbidden rule.
- Kept options as a prior artifact only; no options-native candidate edge was
  introduced.

## Self-Review

- Confirmed every file required by `validate_required_files()` exists.
- Confirmed all research parameters in `research/priority-register.yaml` remain
  `OPEN`.
- Confirmed no trading threshold, feed, sizing value, or live parameter was
  invented.
- Confirmed no `.superpowers/` files are tracked.

## Concerns

- Policy schemas are structural skeletons. Stronger semantic validation should
  be added before Phase 1 begins.
- Pytest still emits the pre-existing `pytest_asyncio` deprecation warning.

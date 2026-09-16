# Task 3 Report: Phase 0 Artifact Validator

## Status

Implemented Task 3 as specified.

## Commit

- `466817a feat: add phase 0 artifact validator`

## Files Changed

- Created `tools/validate_phase0.py`
- Created `tests/specification/test_phase0_validator.py`

## TDD Evidence

1. RED: `python -m pytest tests/specification/test_phase0_validator.py -v`
   - Exit code: 1
   - Result: pytest collection failed with `ModuleNotFoundError: No module named 'tools'`, matching the missing validator module expected before implementation.

2. GREEN: `python -m pytest tests/specification/test_phase0_validator.py -v`
   - Exit code: 0
   - Result: 4 passed.

3. Broader regression check: `python -m pytest -v`
   - Exit code: 0
   - Result: 14 passed.

4. Expected failing full validator check: `python tools/validate_phase0.py`
   - Exit code: 1
   - Result: failed with `ValueError: missing Phase 0 files: configs/graphs/node-registry.yaml, configs/features/feature-catalog.yaml, configs/contracts/label-contracts.yaml, configs/features/feature-dependency-graph.yaml, configs/features/freshness-policy.yaml, configs/graphs/critical-dependency-matrix.yaml, configs/history/historical-match-policy.yaml, configs/decision/conflict-policy.yaml, configs/risk/portfolio-sizing-policy.yaml, configs/execution/cost-fill-policy.yaml, configs/runtime/degraded-mode-policy.yaml, configs/runtime/kill-switch-policy.yaml, research/priority-register.yaml, research/experiment-ledger/README.md`.

## Implementation Notes

- The validator exposes the exact public functions requested in the brief.
- JSON schemas under `schemas/*.schema.json` are checked with `Draft202012Validator.check_schema`.
- Required Phase 0 artifact paths are checked deterministically before file-specific YAML validation.
- The validator keeps null and state semantics delegated to the Phase 0 artifact contracts and schemas; this task only adds the deterministic artifact validator requested by the brief.
- No files under `engine/`, `brand.py`, `run_daily.py`, Notion delivery, or Telegram delivery were touched.
- `.superpowers/sdd` remains scratch workspace; this report is not committed.

## Self-Review

- Scope matches Task 3: only `tools/validate_phase0.py` and `tests/specification/test_phase0_validator.py` were committed.
- The validator tests cover the required helper behaviors: required keys, duplicate IDs, research parameter status requirement, and YAML mapping load.
- The full validator intentionally fails at this phase because Phase 0 YAML and README artifacts are still missing.
- Remaining warning: pytest emits a pre-existing `pytest_asyncio` deprecation warning about `asyncio_default_fixture_loop_scope` being unset.

# Task 2 Report: Core JSON Schemas

## Status

Completed.

## Scope

Implemented the Phase 0 core JSON Schema layer requested by `task-2-brief.md`.

Created:

- `schemas/feature_value.schema.json`
- `schemas/unified_market_state.schema.json`
- `schemas/candidate_action.schema.json`
- `schemas/trade_contract.schema.json`
- `schemas/outcome_label.schema.json`
- `schemas/prediction.schema.json`
- `schemas/final_decision.schema.json`
- `schemas/llm-meta-output.schema.json`
- `tests/specification/test_phase0_schemas.py`

No files under `engine/`, `brand.py`, `run_daily.py`, Notion delivery, or Telegram delivery were changed.

## TDD Evidence

1. Added `tests/specification/test_phase0_schemas.py` with the valid and invalid examples from the task brief.
2. Ran `python -m pytest tests/specification/test_phase0_schemas.py -v`.
3. Confirmed the red failure: 9 tests failed because the requested schema files did not exist.
4. Added the eight JSON Schema Draft 2020-12 schema files.
5. Re-ran `python -m pytest tests/specification/test_phase0_schemas.py -v`.
6. Confirmed the green result: 9 tests passed.

## Implementation Notes

- Every schema declares JSON Schema Draft 2020-12 via `$schema`.
- Every schema is a top-level object with `additionalProperties: false`.
- Required enum values were added verbatim from the brief.
- Timestamp fields use `{ "type": "string", "format": "date-time" }`.
- Probability-like fields use `{ "type": "number", "minimum": 0, "maximum": 1 }`.
- Feature value status keeps `UNKNOWN` out of the allowed enum, preserving separate handling for missing, stale, unavailable, not applicable, null, zero, and false states.
- `llm-meta-output.schema.json` allows only `LONG`, `SHORT`, `WAIT`, and `NO_TRADE` for `recommended_action`, so `SUBMIT_ORDER` is rejected.
- `outcome_label.schema.json` includes `AMBIGUOUS` and accepts null return/slippage fields for ambiguous or unavailable realized values.

## Verification

Command:

```powershell
python -m pytest tests/specification/test_phase0_schemas.py -v
```

Result:

```text
9 passed in 0.16s
```

Additional check:

```powershell
git diff --cached --check
```

Result: no whitespace errors reported before commit.

Post-commit review:

```powershell
git show --check --oneline HEAD
```

Result: no whitespace errors reported for the commit.

## Commit

Created commit:

```text
3f0c2080a906d2f4e375a94894f98a658f153062 feat: add phase 0 core schemas
```

## Self-Review

- Confirmed the commit includes only `schemas/` and `tests/specification/test_phase0_schemas.py`.
- Confirmed no `.superpowers/` files were committed.
- Confirmed no engine, brand, run_daily, Notion, or Telegram delivery code was touched.
- Confirmed the invalid `FeatureValue` `UNKNOWN` status is rejected by enum.
- Confirmed the invalid LLM `SUBMIT_ORDER` action is rejected by enum.
- Confirmed the valid examples in the brief validate successfully.

## Concerns

- The test run emits an environment-level `pytest_asyncio` deprecation warning for unset loop scope. This task did not change pytest configuration because it is outside the Task 2 schema scope.
- JSON Schema cannot compare feature `observed_at` values against `observation_time` without additional validation logic, so the no-lookahead rule remains a policy/tooling concern for later Phase 0 validation.

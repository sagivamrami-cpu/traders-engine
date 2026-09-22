# Task 5 Report: Feature Catalog

## Status

Implemented Task 5.

## Scope

Created `configs/features/feature-catalog.yaml` and updated `tests/specification/test_phase0_configs.py`.

No changes were made to `engine/`, `brand.py`, `run_daily.py`, Notion delivery code, Telegram delivery code, or the existing node registry artifact.

## Implementation

- Added a feature catalog specification test using `validate_feature_catalog` and `load_yaml`.
- Created `configs/features/feature-catalog.yaml` with `version: feature-catalog-0.1.0`.
- Added the exact required `null_semantics` values:
  - `zero`
  - `false`
  - `missing`
  - `unknown`
  - `unavailable`
  - `not_applicable`
  - `stale`
- Added required feature families:
  - `data.provenance`
  - `shared.context`
  - `tr.location`
  - `tr.pattern`
  - `tr.vector`
  - `tr.retest`
  - `order_flow.master`
  - `options.prior`
  - `regime.market`
  - `risk.geometry`
- Added all 26 minimum feature entries from the task brief.
- Each feature entry includes `id`, `dtype`, `unit`, `status_values`, `source`, `observed_at_required`, `computed_at_required`, `engine_version_required`, `confidence_required`, and `research_parameters`.
- `tr.vector.recovery_pct` includes `research_parameters: [tr.vector.recovery_pct.thresholds]`.

## TDD Evidence

### RED

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_feature_catalog_has_null_semantics_and_required_families -v
```

Result: failed as expected because `configs/features/feature-catalog.yaml` did not exist.

### GREEN

Command:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_feature_catalog_has_null_semantics_and_required_families -v
```

Result: passed after creating the feature catalog and quoting `"false"` so YAML parses it as a string.

## Verification

Focused test:

```powershell
python -m pytest tests/specification/test_phase0_configs.py::test_feature_catalog_has_null_semantics_and_required_families -v
```

Result: 1 passed.

All config tests:

```powershell
python -m pytest tests/specification/test_phase0_configs.py -v
```

Result: 3 passed.

Pytest emitted the existing `pytest_asyncio` deprecation warning about `asyncio_default_fixture_loop_scope` being unset.

## Self-Review

- Confirmed the committed diff only touches `configs/features/feature-catalog.yaml` and `tests/specification/test_phase0_configs.py`.
- Confirmed all 26 minimum feature IDs are present.
- Confirmed every feature entry has the required keys.
- Confirmed the catalog version is `feature-catalog-0.1.0`.
- Confirmed the loaded `null_semantics` list matches the exact required string values.
- Confirmed no `.superpowers/` files were committed.

## Commit

`cca66adbbbfe3c754336ea288dacbed7788eea38 feat: add phase 0 feature catalog`

## Concerns

The focused and full config tests pass, but pytest emits an existing `pytest_asyncio` deprecation warning unrelated to this task.

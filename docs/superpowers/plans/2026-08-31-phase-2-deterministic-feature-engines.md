# Phase 2 Deterministic Feature Engines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Phase 1 point-in-time normalized bars into deterministic FeatureValue objects and UnifiedMarketState snapshots for the first fixture-backed vertical slice.

**Architecture:** Add a separate `trading_system/features` package that consumes `NormalizedBar` records and emits Phase 0 schema-compatible feature payloads. Add a `UnifiedMarketState` builder that composes feature outputs into versioned snapshots without candidate generation, labels, model inference, or trading decisions.

**Tech Stack:** Python 3.9+, pytest, PyYAML, jsonschema, dataclasses, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No model training starts in Phase 2.
- No candidate generation, labels, backtesting, broker calls, or live trading is allowed.
- Every feature must validate against `schemas/feature_value.schema.json`.
- Every UnifiedMarketState snapshot must validate against `schemas/unified_market_state.schema.json`.
- Feature computation may use only records available at the snapshot observation time.
- Missing, stale, unavailable, not applicable, and invalid source states must not be coerced to zero.
- Phase 2 fixture logic must remain deterministic and replayable.
- Real production data sources remain blocked as `OPEN_HUMAN_DECISION`.

---

## File Structure

Create or modify these files only:

- `configs/features/feature-engine-registry.yaml`: Phase 2 engine versions and supported features.
- `configs/features/feature-catalog.yaml`: add Phase 2 fixture price-action feature ids.
- `trading_system/features/__init__.py`: feature package exports.
- `trading_system/features/contracts.py`: FeatureValue and UnifiedMarketState dataclasses.
- `trading_system/features/registry.py`: feature catalog and engine registry loading.
- `trading_system/features/price_action.py`: deterministic OHLCV-derived feature calculations.
- `trading_system/features/market_state.py`: UnifiedMarketState snapshot builder.
- `tools/validate_phase2.py`: validates configs, feature payloads, UMS payloads, and replay stability.
- `tests/features/test_feature_contracts.py`: schema-compatible FeatureValue and UMS tests.
- `tests/features/test_price_action_features.py`: deterministic feature engine tests.
- `tests/features/test_market_state.py`: point-in-time UMS snapshot tests.
- `tests/features/test_phase2_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-2-deterministic-feature-engines.md`: Phase 2 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- Candidate, label, model, backtest, broker, or live execution modules

---

## Implementation Tasks

### Task 1: Feature Contracts

**Files:**
- Create: `trading_system/features/__init__.py`
- Create: `trading_system/features/contracts.py`
- Create: `tests/features/test_feature_contracts.py`

**Interfaces:**
- Consumes: `schemas/feature_value.schema.json`, `schemas/unified_market_state.schema.json`
- Produces: `FeatureValue.to_payload() -> dict`, `UnifiedMarketState.to_payload() -> dict`

- [ ] **Step 1: Write failing tests for payload contracts**

Tests must create one `FeatureValue` and one `UnifiedMarketState`, call `to_payload()`, and validate both payloads against Phase 0 schemas.

- [ ] **Step 2: Run contract tests**

Run: `python -m pytest tests/features/test_feature_contracts.py -v`

Expected: fail because `trading_system.features` does not exist yet.

- [ ] **Step 3: Implement contracts**

Implement frozen dataclasses with stable payload serialization. Datetime values must serialize as UTC ISO strings ending with `Z`.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/features/test_feature_contracts.py -v`

Expected: pass.

---

### Task 2: Feature Engine Registry

**Files:**
- Modify: `configs/features/feature-catalog.yaml`
- Create: `configs/features/feature-engine-registry.yaml`
- Create: `trading_system/features/registry.py`
- Create: `tests/features/test_price_action_features.py`

**Interfaces:**
- Consumes: `configs/features/feature-catalog.yaml`
- Produces: `load_feature_engine_registry(path: Path) -> FeatureEngineRegistry`

- [ ] **Step 1: Write registry tests**

Tests must verify that the registry is versioned, references feature ids from the Phase 0 feature catalog, and declares deterministic engine versions.

- [ ] **Step 2: Run registry tests**

Run: `python -m pytest tests/features/test_price_action_features.py::test_feature_engine_registry_matches_catalog -v`

Expected: fail because registry file and loader do not exist.

- [ ] **Step 3: Implement registry config and loader**

Create registry entries for `data.provenance`, `price.action`, and `regime.fixture`.

- [ ] **Step 4: Run registry tests**

Run: `python -m pytest tests/features/test_price_action_features.py::test_feature_engine_registry_matches_catalog -v`

Expected: pass.

---

### Task 3: Deterministic Price Action Features

**Files:**
- Create: `trading_system/features/price_action.py`
- Modify: `tests/features/test_price_action_features.py`

**Interfaces:**
- Consumes: `NormalizedBar`, prior available `NormalizedBar | None`
- Produces: `compute_price_action_features(record, previous_record, computed_at) -> list[FeatureValue]`

- [ ] **Step 1: Write price action tests**

Tests must verify:

- `data.symbol` equals canonical symbol.
- `data.closed_bar` is `true`.
- `data.freshness_status` preserves stale/missing/invalid source status without zero coercion.
- `price.return_pct` equals close-to-close percent when a previous valid bar exists.
- `price.range_pct` equals `(high - low) / close`.
- `price.body_pct` equals `abs(close - open) / close`.
- unavailable previous bar makes `price.return_pct` status `UNAVAILABLE`.

- [ ] **Step 2: Run price action tests**

Run: `python -m pytest tests/features/test_price_action_features.py -v`

Expected: fail because price action engine does not exist.

- [ ] **Step 3: Implement price action engine**

Map Phase 1 statuses to Phase 0 statuses:

- `VALID` -> `VALID`
- `CORRECTED` -> `VALID`
- `MISSING` -> `MISSING`
- `STALE` -> `STALE`
- `INVALID` -> `UNAVAILABLE`
- `UNKNOWN` -> `UNAVAILABLE`

- [ ] **Step 4: Run price action tests**

Run: `python -m pytest tests/features/test_price_action_features.py -v`

Expected: pass.

---

### Task 4: Unified Market State Builder

**Files:**
- Create: `trading_system/features/market_state.py`
- Create: `tests/features/test_market_state.py`

**Interfaces:**
- Consumes: normalized records, symbol, observation time
- Produces: `build_unified_market_state(records, symbol, observation_time, computed_at) -> UnifiedMarketState`

- [ ] **Step 1: Write market state tests**

Tests must verify:

- snapshot uses the latest record available at `observation_time`.
- delayed records are excluded until their `available_at`.
- snapshot id is deterministic for same symbol/time/features.
- `data_quality` is `VALID` when all required fixture features are valid.
- `data_quality` is `DEGRADED` when any required feature is missing/stale/unavailable.
- output validates against `schemas/unified_market_state.schema.json`.

- [ ] **Step 2: Run market state tests**

Run: `python -m pytest tests/features/test_market_state.py -v`

Expected: fail because market state builder does not exist.

- [ ] **Step 3: Implement market state builder**

Use Phase 1 point-in-time helpers and Phase 2 price action features. The builder must not generate candidates or labels.

- [ ] **Step 4: Run market state tests**

Run: `python -m pytest tests/features/test_market_state.py -v`

Expected: pass.

---

### Task 5: Validator and Report

**Files:**
- Create: `tools/validate_phase2.py`
- Create: `tests/features/test_phase2_validator.py`
- Create: `docs/implementation-reports/phase-2-deterministic-feature-engines.md`

**Interfaces:**
- Consumes: Phase 0 schemas, Phase 1 normalized fixture replay, Phase 2 feature engines.
- Produces: deterministic `python tools/validate_phase2.py` command.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase2.py` and assert exit code 0 and output `Phase 2 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/features/test_phase2_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator**

Validator must:

- validate `feature-engine-registry.yaml`.
- normalize fixture rows using Phase 1.
- build at least two UnifiedMarketState snapshots.
- validate every feature payload against `feature_value.schema.json`.
- validate every UMS payload against `unified_market_state.schema.json`.
- prove replay stability by building the same snapshot twice and comparing payloads.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- `python tools/validate_phase2.py` passes.
- Every generated feature payload validates against `schemas/feature_value.schema.json`.
- Every generated UMS payload validates against `schemas/unified_market_state.schema.json`.
- Point-in-time UMS construction excludes records unavailable at observation time.
- Missing, stale, invalid, unknown, and unavailable states are not coerced to numeric zero.
- No candidate generation, labels, model training, backtesting, broker integration, or live execution code is added.

# Phase 4 Fixture Dataset Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fixture-only Dataset Factory that joins UnifiedMarketState, CandidateAction, TradeContract, and OutcomeLabel artifacts into candidate training rows.

**Architecture:** Add `trading_system/datasets` as a metadata and row-construction layer. It consumes existing Phase 1-3 artifacts, produces schema-compatible candidate rows, keeps rejected and ambiguous candidates visible, and implements deterministic time-series split assignment without model training.

**Tech Stack:** Python 3.9+, pytest, jsonschema, dataclasses, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No model training starts in Phase 4.
- A training row is a Candidate Snapshot, not a candle.
- Rejected candidates must be present in the dataset output and excluded from training.
- Ambiguous labels must be present in the dataset output and excluded from training.
- No random split is allowed for time-series training or evaluation.
- Every dataset row must carry schema, feature, label, contract, graph, and source provenance.
- No backtesting engine, broker integration, live execution, prediction API, or capital allocation logic is allowed.

---

## File Structure

Create or modify these files only:

- `schemas/candidate_training_row.schema.json`: dataset row contract.
- `configs/datasets/fixture-dataset-policy.yaml`: fixture dataset and split policy.
- `trading_system/datasets/__init__.py`: dataset package exports.
- `trading_system/datasets/contracts.py`: CandidateTrainingRow dataclass.
- `trading_system/datasets/factory.py`: fixture row construction.
- `trading_system/datasets/splits.py`: deterministic chronological split assignment.
- `tools/validate_phase4.py`: validates fixture dataset rows and split policy.
- `tests/datasets/test_dataset_contracts.py`: row schema tests.
- `tests/datasets/test_dataset_factory.py`: eligible, rejected, ambiguous row tests.
- `tests/datasets/test_splits.py`: no-random chronological split tests.
- `tests/datasets/test_phase4_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-4-fixture-dataset-factory.md`: Phase 4 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- model, training, backtest, broker, or live execution modules

---

## Implementation Tasks

### Task 1: Dataset Row Contract

**Files:**
- Create: `schemas/candidate_training_row.schema.json`
- Create: `trading_system/datasets/__init__.py`
- Create: `trading_system/datasets/contracts.py`
- Create: `tests/datasets/test_dataset_contracts.py`

**Interfaces:**
- Produces: `CandidateTrainingRow.to_payload() -> dict`

- [ ] **Step 1: Write failing contract test**

Validate one complete row against `candidate_training_row.schema.json`.

- [ ] **Step 2: Run contract test**

Run: `python -m pytest tests/datasets/test_dataset_contracts.py -v`

Expected: fail because dataset package and schema do not exist.

- [ ] **Step 3: Implement schema and dataclass**

Required row fields:

- `row_id`
- `dataset_id`
- `dataset_version`
- `snapshot_id`
- `candidate_id`
- `symbol`
- `observation_time`
- `graph_id`
- `graph_version`
- `direction`
- `candidate_status`
- `features`
- `feature_schema_version`
- `contract_version`
- `label_version`
- `outcome_class`
- `label_quality`
- `included_in_training`
- `exclusion_reasons`
- `split`
- `source_hashes`

- [ ] **Step 4: Run contract test**

Run: `python -m pytest tests/datasets/test_dataset_contracts.py -v`

Expected: pass.

---

### Task 2: Fixture Dataset Factory

**Files:**
- Create: `configs/datasets/fixture-dataset-policy.yaml`
- Create: `trading_system/datasets/factory.py`
- Create: `tests/datasets/test_dataset_factory.py`

**Interfaces:**
- Consumes: `UnifiedMarketState`, `CandidateAction`, `TradeContract | None`, `OutcomeLabel | None`
- Produces: `build_candidate_training_row(...) -> CandidateTrainingRow`

- [ ] **Step 1: Write factory tests**

Tests must verify:

- eligible candidate with high-quality label is included in training.
- rejected candidate is kept but excluded from training.
- ambiguous label is kept but excluded from training.
- row id is deterministic.
- row payload validates against `candidate_training_row.schema.json`.

- [ ] **Step 2: Run factory tests**

Run: `python -m pytest tests/datasets/test_dataset_factory.py -v`

Expected: fail because factory does not exist.

- [ ] **Step 3: Implement factory**

Build rows from existing payload objects and compute `row_id` from stable JSON of snapshot id, candidate id, graph version, contract version, label version, and feature payloads.

- [ ] **Step 4: Run factory tests**

Run: `python -m pytest tests/datasets/test_dataset_factory.py -v`

Expected: pass.

---

### Task 3: Chronological Split Policy

**Files:**
- Create: `trading_system/datasets/splits.py`
- Create: `tests/datasets/test_splits.py`

**Interfaces:**
- Produces: `assign_chronological_split(observation_time, boundaries) -> str`

- [ ] **Step 1: Write split tests**

Tests must verify train/validation/test assignment by time boundary and no dependence on random state or row order.

- [ ] **Step 2: Run split tests**

Run: `python -m pytest tests/datasets/test_splits.py -v`

Expected: fail because split module does not exist.

- [ ] **Step 3: Implement split helper**

Return `TRAIN`, `VALIDATION`, or `TEST` from explicit UTC boundaries.

- [ ] **Step 4: Run split tests**

Run: `python -m pytest tests/datasets/test_splits.py -v`

Expected: pass.

---

### Task 4: Validator and Report

**Files:**
- Create: `tools/validate_phase4.py`
- Create: `tests/datasets/test_phase4_validator.py`
- Create: `docs/implementation-reports/phase-4-fixture-dataset-factory.md`

**Interfaces:**
- Consumes: Phase 1-3 fixture artifacts.
- Produces: deterministic `python tools/validate_phase4.py` command.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase4.py` and assert exit code 0 and output `Phase 4 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/datasets/test_phase4_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator**

Validator must build one included row, one rejected excluded row, and one ambiguous excluded row, validate each row payload, and prove row id determinism.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
python tools/validate_phase4.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- `python tools/validate_phase2.py` passes.
- `python tools/validate_phase3.py` passes.
- `python tools/validate_phase4.py` passes.
- Candidate rows, not candles, are the dataset unit.
- Rejected and ambiguous rows remain present and excluded from training.
- Chronological split assignment has no randomness.
- No model training, prediction, backtesting, broker integration, or live execution code is added.

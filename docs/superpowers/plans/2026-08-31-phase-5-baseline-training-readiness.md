# Phase 5 Baseline Training Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a research-only baseline training harness with explicit readiness gates that block meaningless or unsafe model training.

**Architecture:** Add `trading_system/models` as an offline research layer. It consumes candidate training rows, validates chronological split and class requirements, can train a deterministic majority-class baseline when requirements are met, and emits a versioned training run manifest with promotion permanently disabled.

**Tech Stack:** Python 3.9+, pytest, jsonschema, dataclasses, collections, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No live trading, broker integration, order routing, or capital allocation logic is allowed.
- No random split is allowed for time-series training or evaluation.
- No model may train on rejected, ambiguous, missing-label, or excluded rows.
- No edge claim is accepted from the baseline model.
- Promotion is always blocked in Phase 5.
- The fixture dataset must be blocked from training because it has insufficient included rows and classes.
- Training output must be a manifest only; no binary model artifact is written.

---

## File Structure

Create or modify these files only:

- `schemas/model_training_run.schema.json`: training run manifest contract.
- `configs/models/baseline-training-policy.yaml`: research-only training readiness policy.
- `trading_system/models/__init__.py`: model package exports.
- `trading_system/models/contracts.py`: ModelTrainingRun dataclass.
- `trading_system/models/readiness.py`: readiness checks.
- `trading_system/models/baseline.py`: majority-class baseline training harness.
- `tools/validate_phase5.py`: validates blocked fixture training and trainable synthetic examples.
- `tests/models/test_model_contracts.py`: manifest schema tests.
- `tests/models/test_training_readiness.py`: readiness gate tests.
- `tests/models/test_baseline_training.py`: blocked and trained baseline tests.
- `tests/models/test_phase5_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-5-baseline-training-readiness.md`: Phase 5 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, or capital allocation modules

---

## Implementation Tasks

### Task 1: Training Run Contract

**Files:**
- Create: `schemas/model_training_run.schema.json`
- Create: `trading_system/models/__init__.py`
- Create: `trading_system/models/contracts.py`
- Create: `tests/models/test_model_contracts.py`

**Interfaces:**
- Produces: `ModelTrainingRun.to_payload() -> dict`

- [ ] **Step 1: Write failing contract tests**

Validate both `BLOCKED` and `TRAINED` training run payloads against the schema.

- [ ] **Step 2: Run contract tests**

Run: `python -m pytest tests/models/test_model_contracts.py -v`

Expected: fail because model package and schema do not exist.

- [ ] **Step 3: Implement schema and dataclass**

The schema must require run id, status, dataset provenance, policy version, split summary, class distribution, metrics, blocked reasons, and `promotion_allowed`.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/models/test_model_contracts.py -v`

Expected: pass.

---

### Task 2: Training Readiness Gates

**Files:**
- Create: `configs/models/baseline-training-policy.yaml`
- Create: `trading_system/models/readiness.py`
- Create: `tests/models/test_training_readiness.py`

**Interfaces:**
- Produces: `evaluate_training_readiness(rows, policy) -> TrainingReadinessResult`

- [ ] **Step 1: Write readiness tests**

Tests must verify:

- excluded rows are ignored.
- insufficient train rows blocks training.
- missing validation rows blocks training.
- single-class included rows block training.
- two classes with train and validation rows pass readiness.

- [ ] **Step 2: Run readiness tests**

Run: `python -m pytest tests/models/test_training_readiness.py -v`

Expected: fail because readiness module does not exist.

- [ ] **Step 3: Implement readiness checks**

Use only rows where `included_in_training=true`. Count classes from `outcome_class`. Count splits from explicit `split`; do not shuffle.

- [ ] **Step 4: Run readiness tests**

Run: `python -m pytest tests/models/test_training_readiness.py -v`

Expected: pass.

---

### Task 3: Majority Baseline Harness

**Files:**
- Create: `trading_system/models/baseline.py`
- Create: `tests/models/test_baseline_training.py`

**Interfaces:**
- Consumes: `CandidateTrainingRow` rows and `TrainingPolicy`.
- Produces: `train_majority_baseline(rows, policy, created_at) -> ModelTrainingRun`

- [ ] **Step 1: Write baseline tests**

Tests must verify:

- fixture-sized dataset returns `BLOCKED`.
- trainable synthetic rows return `TRAINED`.
- baseline class is the most common training class.
- validation accuracy is deterministic.
- `promotion_allowed` is always false.

- [ ] **Step 2: Run baseline tests**

Run: `python -m pytest tests/models/test_baseline_training.py -v`

Expected: fail because baseline module does not exist.

- [ ] **Step 3: Implement baseline harness**

Train only a majority-class baseline. Do not write binary artifacts. Metrics are manifest values only.

- [ ] **Step 4: Run baseline tests**

Run: `python -m pytest tests/models/test_baseline_training.py -v`

Expected: pass.

---

### Task 4: Validator and Report

**Files:**
- Create: `tools/validate_phase5.py`
- Create: `tests/models/test_phase5_validator.py`
- Create: `docs/implementation-reports/phase-5-baseline-training-readiness.md`

**Interfaces:**
- Consumes: Phase 4 dataset rows.
- Produces: deterministic `python tools/validate_phase5.py` command.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase5.py` and assert exit code 0 and output `Phase 5 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/models/test_phase5_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator**

Validator must prove fixture rows are blocked, synthetic trainable rows can train, and both manifests validate against the schema.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
python tools/validate_phase4.py
python tools/validate_phase5.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- `python tools/validate_phase2.py` passes.
- `python tools/validate_phase3.py` passes.
- `python tools/validate_phase4.py` passes.
- `python tools/validate_phase5.py` passes.
- Fixture dataset training is blocked with explicit readiness reasons.
- Synthetic trainable rows can produce a deterministic research-only majority baseline.
- Promotion remains disabled.
- No broker, live execution, capital allocation, or edge claim is added.

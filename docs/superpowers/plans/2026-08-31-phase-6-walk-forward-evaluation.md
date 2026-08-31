# Phase 6 Walk Forward Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add research-only walk-forward evaluation, prediction payload validation, calibration metrics, and promotion-gate reporting.

**Architecture:** Add `trading_system/evaluation` as an offline report layer above Phase 5. It consumes candidate training rows and model training manifests, creates schema-compatible prediction payloads, evaluates chronological windows, calculates simple calibration metrics, and emits a promotion gate that remains blocked without real out-of-sample evidence and human approval.

**Tech Stack:** Python 3.9+, pytest, jsonschema, dataclasses, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No live trading, broker integration, order routing, or capital allocation logic is allowed.
- No random split is allowed for time-series evaluation.
- Evaluation windows must be chronological: train rows precede validation rows.
- Every prediction payload must validate against `schemas/prediction.schema.json`.
- Every evaluation report must validate against `schemas/model_evaluation_report.schema.json`.
- Calibration metrics must be explicit; no edge claim may be inferred from accuracy alone.
- Promotion is always blocked in Phase 6 without explicit human approval, shadow evidence, paper evidence, cost/fill evidence, and sufficient unseen windows.

---

## File Structure

Create or modify these files only:

- `schemas/model_evaluation_report.schema.json`: evaluation report contract.
- `configs/evaluation/walk-forward-policy.yaml`: evaluation and promotion gate policy.
- `trading_system/evaluation/__init__.py`: evaluation package exports.
- `trading_system/evaluation/contracts.py`: PredictionPayload, EvaluationWindow, ModelEvaluationReport dataclasses.
- `trading_system/evaluation/predictions.py`: majority-baseline prediction payload builder.
- `trading_system/evaluation/metrics.py`: accuracy, brier score, and expected calibration error.
- `trading_system/evaluation/walk_forward.py`: chronological window construction and evaluation.
- `trading_system/evaluation/promotion.py`: promotion gate reason builder.
- `tools/validate_phase6.py`: validates prediction payloads, evaluation reports, and blocked promotion.
- `tests/evaluation/test_evaluation_contracts.py`: schema-compatible prediction and report tests.
- `tests/evaluation/test_metrics.py`: metric tests.
- `tests/evaluation/test_walk_forward.py`: chronological window and evaluation tests.
- `tests/evaluation/test_promotion_gate.py`: promotion gate tests.
- `tests/evaluation/test_phase6_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-6-walk-forward-evaluation.md`: Phase 6 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, or production deployment modules

---

## Implementation Tasks

### Task 1: Evaluation Contracts

**Files:**
- Create: `schemas/model_evaluation_report.schema.json`
- Create: `trading_system/evaluation/__init__.py`
- Create: `trading_system/evaluation/contracts.py`
- Create: `tests/evaluation/test_evaluation_contracts.py`

**Interfaces:**
- Produces: `PredictionPayload.to_payload() -> dict`, `ModelEvaluationReport.to_payload() -> dict`

- [ ] **Step 1: Write failing contract tests**

Validate one prediction payload against `prediction.schema.json` and one report payload against `model_evaluation_report.schema.json`.

- [ ] **Step 2: Run contract tests**

Run: `python -m pytest tests/evaluation/test_evaluation_contracts.py -v`

Expected: fail because evaluation package and report schema do not exist.

- [ ] **Step 3: Implement schema and dataclasses**

Report must include run id, model version, dataset provenance, policy version, window metrics, aggregate metrics, calibration metrics, promotion gate, and `promotion_allowed=false`.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/evaluation/test_evaluation_contracts.py -v`

Expected: pass.

---

### Task 2: Prediction and Metrics

**Files:**
- Create: `trading_system/evaluation/predictions.py`
- Create: `trading_system/evaluation/metrics.py`
- Create: `tests/evaluation/test_metrics.py`

**Interfaces:**
- Produces: `prediction_from_majority_baseline(candidate_id, baseline_class, model_version, feature_schema_version) -> PredictionPayload`

- [ ] **Step 1: Write metric tests**

Tests must verify deterministic majority prediction probabilities, accuracy, Brier score for TARGET_FIRST, and expected calibration error.

- [ ] **Step 2: Run metric tests**

Run: `python -m pytest tests/evaluation/test_metrics.py -v`

Expected: fail because prediction and metric modules do not exist.

- [ ] **Step 3: Implement prediction and metric helpers**

Majority baseline probabilities are one-hot over `TARGET_FIRST`, `STOP_FIRST`, and `EXPIRED`; `AMBIGUOUS` is not predicted.

- [ ] **Step 4: Run metric tests**

Run: `python -m pytest tests/evaluation/test_metrics.py -v`

Expected: pass.

---

### Task 3: Walk Forward Evaluation

**Files:**
- Create: `configs/evaluation/walk-forward-policy.yaml`
- Create: `trading_system/evaluation/walk_forward.py`
- Create: `tests/evaluation/test_walk_forward.py`

**Interfaces:**
- Produces: `build_expanding_windows(rows, min_train_size, validation_size) -> list[EvaluationWindow]`, `evaluate_majority_baseline_walk_forward(rows, policy, created_at) -> ModelEvaluationReport`

- [ ] **Step 1: Write walk-forward tests**

Tests must verify windows are chronological, no random state is accepted, two valid windows can be evaluated from synthetic rows, and fixture-sized inputs produce a blocked report.

- [ ] **Step 2: Run walk-forward tests**

Run: `python -m pytest tests/evaluation/test_walk_forward.py -v`

Expected: fail because walk-forward module does not exist.

- [ ] **Step 3: Implement window builder and evaluator**

Sort rows by observation time. For each window, train uses rows before validation; validation uses the next contiguous block.

- [ ] **Step 4: Run walk-forward tests**

Run: `python -m pytest tests/evaluation/test_walk_forward.py -v`

Expected: pass.

---

### Task 4: Promotion Gate, Validator, and Report

**Files:**
- Create: `trading_system/evaluation/promotion.py`
- Create: `tools/validate_phase6.py`
- Create: `tests/evaluation/test_promotion_gate.py`
- Create: `tests/evaluation/test_phase6_validator.py`
- Create: `docs/implementation-reports/phase-6-walk-forward-evaluation.md`

**Interfaces:**
- Produces: `evaluate_promotion_gate(report, policy) -> dict`

- [ ] **Step 1: Write promotion and validator tests**

Tests must verify promotion remains blocked without human approval, shadow evidence, paper evidence, cost/fill evidence, and enough windows. Validator must print `Phase 6 artifacts validated`.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/evaluation/test_promotion_gate.py tests/evaluation/test_phase6_validator.py -v`

Expected: fail because promotion and validator modules do not exist.

- [ ] **Step 3: Implement promotion gate and validator**

Validator must build blocked fixture evaluation and synthetic trainable evaluation, validate reports, validate predictions, and assert promotion is false.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
python tools/validate_phase4.py
python tools/validate_phase5.py
python tools/validate_phase6.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- `python tools/validate_phase2.py` passes.
- `python tools/validate_phase3.py` passes.
- `python tools/validate_phase4.py` passes.
- `python tools/validate_phase5.py` passes.
- `python tools/validate_phase6.py` passes.
- Prediction payloads validate against `schemas/prediction.schema.json`.
- Evaluation reports validate against `schemas/model_evaluation_report.schema.json`.
- Walk-forward evaluation is chronological and has no random split.
- Promotion remains blocked with explicit reasons.
- No broker, live execution, capital allocation, production deployment, or edge claim is added.

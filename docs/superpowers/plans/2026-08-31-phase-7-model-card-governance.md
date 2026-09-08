# Phase 7 Model Card Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a research-only model card and registry package that records training, evaluation, limitations, blocked promotion reasons, and rollback metadata.

**Architecture:** Add `trading_system/governance` as an artifact layer above Phase 6. It consumes training and evaluation manifests, produces schema-compatible model cards, and keeps approval status blocked until explicit human promotion approval exists.

**Tech Stack:** Python 3.9+, pytest, jsonschema, dataclasses, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No live trading, broker integration, order routing, deployment, or capital allocation logic is allowed.
- No LLM may approve promotion.
- Model card approval status must remain `BLOCKED` without explicit human approval.
- Model cards must preserve dataset, training, evaluation, schema, known limitations, blocked reasons, and rollback target metadata.
- A model card is not an edge claim.

---

## File Structure

Create or modify these files only:

- `schemas/model_card.schema.json`: model card contract.
- `configs/governance/model-card-policy.yaml`: model card requirements and blocked approval policy.
- `trading_system/governance/__init__.py`: governance package exports.
- `trading_system/governance/model_card.py`: model card dataclass and builder.
- `tools/validate_phase7.py`: validates model card payloads.
- `tests/governance/test_model_card.py`: contract and builder tests.
- `tests/governance/test_phase7_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-7-model-card-governance.md`: Phase 7 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, or deployment modules

---

## Implementation Tasks

### Task 1: Model Card Contract and Builder

**Files:**
- Create: `schemas/model_card.schema.json`
- Create: `configs/governance/model-card-policy.yaml`
- Create: `trading_system/governance/__init__.py`
- Create: `trading_system/governance/model_card.py`
- Create: `tests/governance/test_model_card.py`

**Interfaces:**
- Produces: `ModelCard.to_payload() -> dict`, `build_model_card(training_run, evaluation_report, created_at) -> ModelCard`

- [ ] **Step 1: Write failing tests**

Tests must validate a model card payload, prove approval is blocked, and prove blocked reasons include human/shadow/paper/cost-fill evidence gaps.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/governance/test_model_card.py -v`

Expected: fail because governance package and schema do not exist.

- [ ] **Step 3: Implement schema, config, dataclass, and builder**

The builder must copy training/evaluation provenance and refuse to set approval status to approved.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/governance/test_model_card.py -v`

Expected: pass.

---

### Task 2: Validator and Report

**Files:**
- Create: `tools/validate_phase7.py`
- Create: `tests/governance/test_phase7_validator.py`
- Create: `docs/implementation-reports/phase-7-model-card-governance.md`

**Interfaces:**
- Produces: deterministic `python tools/validate_phase7.py` command.

- [ ] **Step 1: Write validator test**

Test must call `python tools/validate_phase7.py` and assert output `Phase 7 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/governance/test_phase7_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator and report**

Validator must build a synthetic training run and evaluation report, create a model card, validate it against schema, and assert approval status is blocked.

- [ ] **Step 4: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
python tools/validate_phase4.py
python tools/validate_phase5.py
python tools/validate_phase6.py
python tools/validate_phase7.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance -v` passes.
- `python tools/validate_phase7.py` passes.
- Model card validates against `schemas/model_card.schema.json`.
- Approval status remains `BLOCKED`.
- Blocked reasons include missing human approval, shadow evidence, paper evidence, and cost/fill evidence.
- No live execution, broker, deployment, or capital allocation code is added.

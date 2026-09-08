# Phase 12 Real Data Readiness Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a machine-readable readiness checklist that shows exactly which real-data inputs and approvals are still missing before production-grade dataset construction or model training.

**Architecture:** Create a config-driven readiness checklist and a small `trading_system/research/readiness.py` reporter. The report is intentionally blocked by default because the current repo has fixture/synthetic evidence only and no human-approved production inputs.

**Tech Stack:** Python 3.9+, pytest, jsonschema, argparse, yaml, pathlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No network data fetches are allowed.
- No vendor is approved by readiness reporting.
- Fixture and synthetic data are not production evidence.
- Real-data readiness must remain blocked until explicit human inputs and approvals exist.
- No model training changes, backtesting engine, broker integration, live execution, deployment, or capital allocation logic is allowed.

---

## File Structure

Create these files only:

- `schemas/real_data_readiness_report.schema.json`: readiness report contract.
- `configs/research/real-data-readiness-checklist.yaml`: default required-input checklist.
- `trading_system/research/readiness.py`: checklist loader and report builder.
- `tools/real_data_readiness.py`: CLI that prints readiness JSON.
- `tools/validate_phase12.py`: deterministic Phase 12 validator.
- `tests/research/test_real_data_readiness.py`: readiness behavior tests.
- `tests/research/test_phase12_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`: Phase 12 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or production model promotion modules

---

## Implementation Tasks

### Task 1: Readiness Checklist Contract and Reporter

**Files:**
- Create: `schemas/real_data_readiness_report.schema.json`
- Create: `configs/research/real-data-readiness-checklist.yaml`
- Create: `trading_system/research/readiness.py`
- Create: `tests/research/test_real_data_readiness.py`

**Interfaces:**
- Produces: `load_real_data_readiness_checklist(path: Path) -> RealDataReadinessChecklist` and `build_real_data_readiness_report(checklist, created_at) -> RealDataReadinessReport`.

- [ ] **Step 1: Write failing tests**

Tests must verify the checklist schema validates, report status is `BLOCKED`, all required fixture-phase gaps are listed as open, blocked actions include production dataset/model/live actions, and no item is marked satisfied by default.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/research/test_real_data_readiness.py -v`

Expected: fail because `readiness.py` does not exist.

- [ ] **Step 3: Implement schema, config, and reporter**

The reporter must copy checklist items into the report, count open and satisfied items, and derive readiness status from item statuses.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/research/test_real_data_readiness.py -v`

Expected: pass.

---

### Task 2: CLI, Validator, and Report

**Files:**
- Create: `tools/real_data_readiness.py`
- Create: `tools/validate_phase12.py`
- Create: `tests/research/test_phase12_validator.py`
- Create: `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`

**Interfaces:**
- Produces: `python tools/real_data_readiness.py` and `python tools/validate_phase12.py`.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase12.py` and assert output `Phase 12 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/research/test_phase12_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement CLI and validator**

CLI prints sorted JSON with trailing newline. Validator loads the default checklist, validates config and report payloads, and verifies the report remains blocked.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
python tools/validate_phase4.py
python tools/validate_phase5.py
python tools/validate_phase6.py
python tools/validate_phase7.py
python tools/validate_phase8.py
python tools/validate_phase9.py
python tools/validate_phase10.py
python tools/validate_phase11.py
python tools/validate_phase12.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase12.py` passes.
- `python tools/real_data_readiness.py` emits schema-valid JSON.
- Default report remains `BLOCKED`.
- Required missing human inputs are explicit.
- No checklist item is satisfied by default.
- Production dataset/model/live actions remain blocked.
- No network fetch, vendor approval, raw copy, model promotion, broker integration, live execution, backtesting engine, deployment, or capital allocation code is added.

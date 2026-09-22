# Phase 10 Raw Data Retention Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit raw-data retention and license policy for user-provided local CSV inputs.

**Architecture:** Extend `trading_system/data_foundation` with a policy loader and retention decision evaluator. The policy allows manifest and dry-run outputs, blocks raw CSV copying/mutation/upload, and records that retention and license approval require a human decision before any production storage path is used.

**Tech Stack:** Python 3.9+, pytest, jsonschema, yaml, pathlib.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No network data fetches are allowed.
- No vendor is approved by local CSV policy validation.
- Raw CSV files are immutable inputs and are not copied or modified.
- Retention approval must be explicit and human-owned.
- Manifest output and dry-run output may be allowed while raw retention remains blocked.
- No model training changes, backtesting engine, broker integration, live execution, deployment, or capital allocation logic is allowed.

---

## File Structure

Create these files only:

- `schemas/raw_data_retention_policy.schema.json`: retention policy contract.
- `configs/data/raw-data-retention-policy.yaml`: default manifest-only local CSV policy.
- `trading_system/data_foundation/storage_policy.py`: policy loader and decision evaluator.
- `tools/validate_phase10.py`: deterministic Phase 10 validator.
- `tests/data_foundation/test_storage_policy.py`: policy behavior tests.
- `tests/data_foundation/test_phase10_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-10-raw-data-retention-policy.md`: Phase 10 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or production model promotion modules

---

## Implementation Tasks

### Task 1: Retention Policy Contract and Evaluator

**Files:**
- Create: `schemas/raw_data_retention_policy.schema.json`
- Create: `configs/data/raw-data-retention-policy.yaml`
- Create: `trading_system/data_foundation/storage_policy.py`
- Create: `tests/data_foundation/test_storage_policy.py`

**Interfaces:**
- Consumes: Phase 8 RawSourceManifest-compatible payload.
- Produces: `load_raw_data_retention_policy(path: Path) -> RawDataRetentionPolicy` and `evaluate_raw_data_retention(policy, manifest) -> RawDataRetentionDecision`.

- [ ] **Step 1: Write failing tests**

Tests must verify the policy schema validates, local CSV manifest-only output is allowed, raw copy/mutation/upload are blocked, retention approval remains false, and source statuses other than `OPEN_HUMAN_DECISION` are blocked.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/data_foundation/test_storage_policy.py -v`

Expected: fail because `storage_policy.py` does not exist.

- [ ] **Step 3: Implement schema, config, and evaluator**

The evaluator must require manifest fields, preserve the raw source status, and return blocked reasons rather than approving retention.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/data_foundation/test_storage_policy.py -v`

Expected: pass.

---

### Task 2: Validator and Report

**Files:**
- Create: `tools/validate_phase10.py`
- Create: `tests/data_foundation/test_phase10_validator.py`
- Create: `docs/implementation-reports/phase-10-raw-data-retention-policy.md`

**Interfaces:**
- Produces: `python tools/validate_phase10.py`.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase10.py` and assert output `Phase 10 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/data_foundation/test_phase10_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator**

Validator checks the policy schema, loads the YAML policy, builds the Phase 8 fixture manifest, evaluates retention, and verifies raw retention remains blocked while manifest-only output is allowed.

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
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase10.py` passes.
- Raw-data retention policy validates against schema.
- Local CSV manifest-only output is allowed.
- Raw copy, mutation, and network upload are blocked by policy.
- Retention approval remains false until explicit human approval.
- Non-`OPEN_HUMAN_DECISION` local CSV source status is blocked.
- No model training changes, backtesting engine, broker integration, live execution, deployment, or capital allocation code is added.

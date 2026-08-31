# Phase 11 Local Source Bundle Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single validation entrypoint for a local CSV source bundle: CSV file, metadata YAML, and raw-data retention policy.

**Architecture:** Create a `trading_system/research/source_bundle.py` module that loads the bundle, runs Phase 8 onboarding, Phase 10 retention evaluation, and Phase 9 dry-run, then emits a source-bundle validation summary. The bundle can be accepted for local dry-run only; it cannot approve production data, raw retention, model promotion, broker use, or capital allocation.

**Tech Stack:** Python 3.9+, pytest, jsonschema, argparse, yaml, pathlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No network data fetches are allowed.
- No vendor is approved by bundle validation.
- Raw CSV files are immutable inputs and are not copied or modified.
- Bundle validation may only accept inputs for `LOCAL_CSV_DRY_RUN`.
- Raw retention, model promotion, broker execution, live trading, and capital allocation remain blocked.
- No model training changes, backtesting engine, broker integration, live execution, deployment, or capital allocation logic is allowed.

---

## File Structure

Create these files only:

- `schemas/source_bundle_validation.schema.json`: source bundle validation contract.
- `trading_system/research/source_bundle.py`: bundle validation orchestrator.
- `tools/validate_local_source_bundle.py`: CLI that prints bundle validation JSON.
- `tools/validate_phase11.py`: deterministic Phase 11 validator.
- `tests/research/test_source_bundle.py`: bundle validation behavior tests.
- `tests/research/test_phase11_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-11-local-source-bundle-validation.md`: Phase 11 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or production model promotion modules

---

## Implementation Tasks

### Task 1: Bundle Validation Contract and Orchestrator

**Files:**
- Create: `schemas/source_bundle_validation.schema.json`
- Create: `trading_system/research/source_bundle.py`
- Create: `tests/research/test_source_bundle.py`

**Interfaces:**
- Consumes: Phase 8 onboarding, Phase 9 dry-run, Phase 10 retention policy.
- Produces: `validate_local_source_bundle(csv_path, metadata_path, retention_policy_path, created_at) -> SourceBundleValidation`.

- [ ] **Step 1: Write failing tests**

Tests must verify the bundle payload validates the schema, the fixture bundle is `ACCEPTED_FOR_DRY_RUN`, promotion remains false, retention remains unapproved, and non-open source status metadata is blocked.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/research/test_source_bundle.py -v`

Expected: fail because `source_bundle.py` does not exist.

- [ ] **Step 3: Implement schema and orchestrator**

The validator loads the three bundle files, runs onboarding, evaluates retention, runs dry-run, and derives final bundle status from those results.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/research/test_source_bundle.py -v`

Expected: pass.

---

### Task 2: CLI, Validator, and Report

**Files:**
- Create: `tools/validate_local_source_bundle.py`
- Create: `tools/validate_phase11.py`
- Create: `tests/research/test_phase11_validator.py`
- Create: `docs/implementation-reports/phase-11-local-source-bundle-validation.md`

**Interfaces:**
- Produces: `python tools/validate_local_source_bundle.py --csv <path> --metadata <yaml> --retention-policy <yaml>` and `python tools/validate_phase11.py`.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase11.py` and assert output `Phase 11 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/research/test_phase11_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement CLI and validator**

CLI prints sorted JSON with trailing newline. Validator runs the fixture source bundle and validates the payload.

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
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase11.py` passes.
- `python tools/validate_local_source_bundle.py --csv <path> --metadata <yaml> --retention-policy <yaml>` emits schema-valid JSON.
- Fixture bundle is accepted for dry-run only.
- Raw retention remains unapproved.
- Model promotion remains false.
- Non-`OPEN_HUMAN_DECISION` local metadata is blocked.
- No network fetch, vendor approval, raw copy, model promotion, broker integration, live execution, backtesting engine, deployment, or capital allocation code is added.

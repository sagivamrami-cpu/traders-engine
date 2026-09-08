# Phase 8 Local CSV Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local OHLCV CSV onboarding path that validates an external file and emits a schema-compatible RawSourceManifest without approving any production vendor.

**Architecture:** Extend `trading_system/data_foundation` with a CSV onboarding module and CLI. The tool reads a local CSV path, enforces required columns, computes immutable raw hash, normalizes rows through existing Phase 1 policies, and returns manifest metadata while keeping production source approval as a human decision.

**Tech Stack:** Python 3.9+, pytest, jsonschema, argparse, csv, pathlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No network data fetches are allowed in Phase 8.
- No vendor is approved by importing a CSV.
- Raw CSV files are immutable inputs and are not copied or modified.
- The onboarding output must validate against `schemas/raw_source_manifest.schema.json`.
- Normalization must reuse existing Phase 1 timestamp and symbol policies.
- Unknown symbols and missing required columns must fail with explicit errors.
- No model training, backtesting, broker integration, live execution, or capital allocation logic is allowed.

---

## File Structure

Create or modify these files only:

- `configs/data/local-csv-onboarding-template.yaml`: documented fixture-safe source metadata template.
- `trading_system/data_foundation/csv_onboarding.py`: CSV inspection and manifest builder.
- `tools/onboard_ohlcv_csv.py`: CLI that prints RawSourceManifest JSON.
- `tools/validate_phase8.py`: validates fixture onboarding.
- `tests/data_foundation/test_csv_onboarding.py`: onboarding module tests.
- `tests/data_foundation/test_phase8_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-8-local-csv-onboarding.md`: Phase 8 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or model training modules

---

## Implementation Tasks

### Task 1: CSV Onboarding Module

**Files:**
- Create: `configs/data/local-csv-onboarding-template.yaml`
- Create: `trading_system/data_foundation/csv_onboarding.py`
- Create: `tests/data_foundation/test_csv_onboarding.py`

**Interfaces:**
- Produces: `build_raw_source_manifest_for_csv(csv_path, metadata, policy, symbol_map, ingested_at) -> dict`

- [ ] **Step 1: Write failing tests**

Tests must verify fixture CSV onboarding validates the raw source manifest schema, missing columns fail, unknown symbols fail, hash and row count are deterministic, and observed date range is UTC.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/data_foundation/test_csv_onboarding.py -v`

Expected: fail because onboarding module does not exist.

- [ ] **Step 3: Implement module and template**

Use existing `sha256_file`, `read_csv_rows`, `normalize_ohlcv_row`, and `raw_source_manifest.schema.json`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/data_foundation/test_csv_onboarding.py -v`

Expected: pass.

---

### Task 2: CLI, Validator, and Report

**Files:**
- Create: `tools/onboard_ohlcv_csv.py`
- Create: `tools/validate_phase8.py`
- Create: `tests/data_foundation/test_phase8_validator.py`
- Create: `docs/implementation-reports/phase-8-local-csv-onboarding.md`

**Interfaces:**
- Produces: `python tools/onboard_ohlcv_csv.py --csv <path> --metadata <yaml>` and `python tools/validate_phase8.py`

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase8.py` and assert output `Phase 8 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/data_foundation/test_phase8_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement CLI and validator**

CLI prints sorted JSON with trailing newline. Validator runs onboarding on the existing fixture and validates the payload.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

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
python tools/validate_phase8.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase8.py` passes.
- Fixture CSV onboarding emits a RawSourceManifest-compatible payload.
- Missing columns fail explicitly.
- Unknown symbols fail explicitly.
- Raw file hash and row count are deterministic.
- Onboarding does not approve any production vendor.
- No model training, backtesting, broker integration, live execution, or capital allocation code is added.

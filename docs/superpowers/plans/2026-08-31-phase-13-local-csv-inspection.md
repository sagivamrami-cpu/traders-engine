# Phase 13 Local CSV Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local CSV inspection tool that prepares user-provided OHLCV files for source-bundle validation without copying raw data or approving production use.

**Architecture:** Extend `trading_system/data_foundation` with a CSV inspection report builder. The builder validates required columns, computes file hash and observed date range, identifies raw symbols, and returns suggested metadata for a single-symbol local CSV in `OPEN_HUMAN_DECISION` status.

**Tech Stack:** Python 3.9+, pytest, jsonschema, argparse, csv/pathlib/datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No network data fetches are allowed.
- No vendor is approved by CSV inspection.
- Raw CSV files are immutable inputs and are not copied or modified.
- Inspection output may suggest metadata only; it must not write metadata files.
- Suggested metadata source status must be `OPEN_HUMAN_DECISION`.
- No model training changes, backtesting engine, broker integration, live execution, deployment, or capital allocation logic is allowed.

---

## File Structure

Create these files only:

- `schemas/local_csv_inspection_report.schema.json`: CSV inspection report contract.
- `trading_system/data_foundation/csv_inspection.py`: inspection and suggested metadata builder.
- `tools/inspect_local_ohlcv_csv.py`: CLI that prints inspection JSON.
- `tools/validate_phase13.py`: deterministic Phase 13 validator.
- `tests/data_foundation/test_csv_inspection.py`: inspection behavior tests.
- `tests/data_foundation/test_phase13_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-13-local-csv-inspection.md`: Phase 13 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or production model promotion modules

---

## Implementation Tasks

### Task 1: CSV Inspection Contract and Builder

**Files:**
- Create: `schemas/local_csv_inspection_report.schema.json`
- Create: `trading_system/data_foundation/csv_inspection.py`
- Create: `tests/data_foundation/test_csv_inspection.py`

**Interfaces:**
- Consumes: `sha256_file`, `read_csv_rows`, `parse_datetime`, Phase 8 required OHLCV columns.
- Produces: `inspect_local_ohlcv_csv(csv_path, metadata_inputs, policy, created_at) -> LocalCsvInspectionReport`.

- [ ] **Step 1: Write failing tests**

Tests must verify the inspection payload validates the schema, fixture inspection is ready for bundle validation, required metadata is suggested with `OPEN_HUMAN_DECISION`, missing columns block inspection, and multi-symbol CSVs are blocked until split.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/data_foundation/test_csv_inspection.py -v`

Expected: fail because `csv_inspection.py` does not exist.

- [ ] **Step 3: Implement schema and builder**

The builder must inspect the local CSV without writing files, derive UTC observed date range through Phase 1 timestamp policy, and avoid using symbol-map approval.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/data_foundation/test_csv_inspection.py -v`

Expected: pass.

---

### Task 2: CLI, Validator, and Report

**Files:**
- Create: `tools/inspect_local_ohlcv_csv.py`
- Create: `tools/validate_phase13.py`
- Create: `tests/data_foundation/test_phase13_validator.py`
- Create: `docs/implementation-reports/phase-13-local-csv-inspection.md`

**Interfaces:**
- Produces: `python tools/inspect_local_ohlcv_csv.py --csv <path> --source-id <id> --canonical-symbol <symbol>` and `python tools/validate_phase13.py`.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase13.py` and assert output `Phase 13 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/data_foundation/test_phase13_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement CLI and validator**

CLI prints sorted JSON with trailing newline. Validator inspects the fixture CSV, validates schema, and checks suggested metadata remains unapproved.

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
python tools/validate_phase13.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase13.py` passes.
- `python tools/inspect_local_ohlcv_csv.py --csv <path> --source-id <id> --canonical-symbol <symbol>` emits schema-valid JSON.
- Fixture CSV inspection is ready for bundle validation.
- Missing columns block inspection explicitly.
- Multi-symbol CSVs are blocked until split.
- Suggested metadata remains `OPEN_HUMAN_DECISION`.
- No network fetch, vendor approval, raw copy, model promotion, broker integration, live execution, backtesting engine, deployment, or capital allocation code is added.

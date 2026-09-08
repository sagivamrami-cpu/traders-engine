# Phase 9 Local CSV Research Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline local CSV research dry-run that connects CSV onboarding through candidate training readiness without approving a vendor or enabling model promotion.

**Architecture:** Create a small `trading_system/research` orchestration layer that reuses Phase 1 normalization, Phase 2 market states, Phase 3 candidates/labels, Phase 4 training rows, and Phase 5 baseline training readiness. The CLI prints a schema-validated summary and never writes artifacts, sends orders, or promotes a model.

**Tech Stack:** Python 3.9+, pytest, jsonschema, argparse, yaml, pathlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- Phase 9 may consume a local CSV path only.
- No network data fetches are allowed.
- No vendor is approved by importing or dry-running a CSV.
- Source status must remain `OPEN_HUMAN_DECISION` for local CSV input.
- The dry-run output must validate against `schemas/offline_research_run.schema.json`.
- The dry-run must reuse existing Phase 1-5 components.
- No live trading, broker integration, backtesting engine, capital allocation, deployment, model promotion, or edge claim is allowed.

---

## File Structure

Create these files only:

- `schemas/offline_research_run.schema.json`: research dry-run summary contract.
- `trading_system/research/__init__.py`: research package marker.
- `trading_system/research/offline_dry_run.py`: local CSV dry-run orchestrator.
- `tools/run_local_csv_dry_run.py`: CLI that prints dry-run JSON.
- `tools/validate_phase9.py`: deterministic Phase 9 validator.
- `tests/research/test_offline_dry_run.py`: dry-run behavior tests.
- `tests/research/test_phase9_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-9-local-csv-research-dry-run.md`: Phase 9 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- broker, live execution, capital allocation, deployment, or production model promotion modules

---

## Implementation Tasks

### Task 1: Offline Dry-Run Contract and Orchestrator

**Files:**
- Create: `schemas/offline_research_run.schema.json`
- Create: `trading_system/research/__init__.py`
- Create: `trading_system/research/offline_dry_run.py`
- Create: `tests/research/test_offline_dry_run.py`

**Interfaces:**
- Consumes: `build_raw_source_manifest_for_csv`, `normalize_ohlcv_row`, `build_unified_market_state`, `generate_fixture_candidate`, `build_fixture_trade_contract`, `label_long_candidate`, `build_candidate_training_row`, `assign_chronological_split`, `train_majority_baseline`.
- Produces: `build_local_csv_research_dry_run(csv_path, metadata, policy, symbol_map, training_policy, created_at) -> OfflineResearchRun`.

- [ ] **Step 1: Write failing tests**

Tests must verify the dry-run payload validates the schema, local CSV source status remains `OPEN_HUMAN_DECISION`, the fixture run is blocked, promotion is false, and counts are deterministic.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/research/test_offline_dry_run.py -v`

Expected: fail because `trading_system.research` does not exist.

- [ ] **Step 3: Implement schema and orchestrator**

The orchestrator should build a raw source manifest, normalize rows, build market-state snapshots at row availability times, generate fixture candidates, label eligible candidates against future bars, convert all candidates into training rows, and run the majority baseline readiness gate.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/research/test_offline_dry_run.py -v`

Expected: pass.

---

### Task 2: CLI, Validator, and Report

**Files:**
- Create: `tools/run_local_csv_dry_run.py`
- Create: `tools/validate_phase9.py`
- Create: `tests/research/test_phase9_validator.py`
- Create: `docs/implementation-reports/phase-9-local-csv-research-dry-run.md`

**Interfaces:**
- Produces: `python tools/run_local_csv_dry_run.py --csv <path> --metadata <yaml>` and `python tools/validate_phase9.py`.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase9.py` and assert output `Phase 9 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/research/test_phase9_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement CLI and validator**

CLI prints sorted JSON with trailing newline. Validator runs the fixture dry-run, validates its payload, and validates CLI output.

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
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python tools/validate_phase9.py` passes.
- Fixture local CSV dry-run emits an OfflineResearchRun-compatible payload.
- Dry-run consumes the Phase 8 local CSV onboarding path.
- Baseline training remains blocked for fixture-sized inputs.
- `promotion_allowed` remains false.
- No network fetch, production vendor approval, live execution, broker integration, backtesting engine, or capital allocation code is added.

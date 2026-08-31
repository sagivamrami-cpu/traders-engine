# Phase 15 Real-Data Safety Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the real-data path so fixture identifiers, agent-authored approvals, weak CSV inspection, and dry-run bypasses cannot unlock production dataset construction.

**Architecture:** Keep the repo research-only. Tighten existing loaders and CLIs with fail-closed validation instead of adding new production flows. Decision approval must resolve to human markdown records under `agent-exchange/decisions/`; local CSV tooling must reject ambiguous or invalid inputs before dry-run.

**Tech Stack:** Python 3.13 in the current workspace, pytest, jsonschema, PyYAML, argparse.

**Spec:** `agent-exchange/inbox/claude-code/2026-08-31T153000Z-claude-code-phase-15-real-data-safety-hardening.md`

## Global Constraints

- No production approval by implication.
- No live trading, broker execution, capital allocation, deployment, or model promotion.
- No committed real CSV payloads or secrets.
- Start each behavior change with a failing test.
- Keep fixture identifiers allowed only for committed fixture tests.
- Keep production dataset construction blocked until explicit human decision records exist.

---

### Task 1: Human Decision Evidence Gate

**Files:**
- Modify: `trading_system/research/readiness.py`
- Modify: `schemas/real_data_decisions.schema.json`
- Modify: `schemas/real_data_readiness_report.schema.json`
- Modify: `tests/research/test_real_data_readiness.py`

**Interfaces:**
- Consumes: `load_real_data_decisions(path: Path)`
- Produces: approved decisions only from YAML under `agent-exchange/decisions/` with evidence markdown records in the same tree.

- [ ] Write failing tests for approved YAML outside `agent-exchange/decisions/`, missing evidence files, evidence outside decisions, and defer decisions.
- [ ] Implement decision path and evidence record validation.
- [ ] Update schemas and report version.
- [ ] Verify `tests/research/test_real_data_readiness.py`.

### Task 2: Readiness Status Semantics

**Files:**
- Modify: `trading_system/research/readiness.py`
- Modify: `schemas/real_data_readiness_report.schema.json`
- Modify: `tests/research/test_real_data_readiness.py`

**Interfaces:**
- Consumes: `build_real_data_readiness_report(...)`
- Produces: no `READY_FOR_PRODUCTION_DATASET` status while production dataset construction remains blocked.

- [ ] Write failing test for the ready-status contradiction.
- [ ] Keep the report `BLOCKED` while `BUILD_PRODUCTION_TRAINING_DATASET` is in `blocked_actions`.
- [ ] Verify readiness tests and Phase 14 validator.

### Task 3: CSV Inspection Hardening

**Files:**
- Modify: `trading_system/data_foundation/csv_inspection.py`
- Modify: `tools/inspect_local_ohlcv_csv.py`
- Modify: `schemas/local_csv_inspection_report.schema.json`
- Modify: `tests/data_foundation/test_csv_inspection.py`

**Interfaces:**
- Consumes: local CSV rows, normalization policy, symbol map.
- Produces: fail-closed inspection for blank symbols, unknown symbols, canonical mismatches, invalid OHLC, duplicate timestamps, and `available_at < observed_at`.

- [ ] Write failing inspection tests for each rejected case.
- [ ] Add optional symbol-map validation to inspection.
- [ ] Rename shape success to avoid implying bundle acceptance.
- [ ] Verify data foundation tests.

### Task 4: Dry-Run Bundle Gate

**Files:**
- Modify: `tools/run_local_csv_dry_run.py`
- Modify: `tests/research/test_offline_dry_run.py`

**Interfaces:**
- Consumes: `validate_local_source_bundle(...)`
- Produces: CLI dry-run requires `--retention-policy` and refuses to bypass bundle validation.

- [ ] Write failing CLI tests for missing retention policy and successful fixture gated dry-run.
- [ ] Implement the CLI gate.
- [ ] Verify research tests.

### Task 5: Fixture Isolation And Output Hygiene

**Files:**
- Modify: `.gitignore`
- Modify: `trading_system/research/offline_dry_run.py`
- Modify: `tests/research/test_offline_dry_run.py`
- Add: `tools/validate_phase15.py`
- Add: `tests/research/test_phase15_validator.py`
- Add: `docs/implementation-reports/phase-15-real-data-safety-hardening.md`
- Add: `agent-exchange/status/2026-08-31T163000Z-codex-phase-15-implementation-status.md`

**Interfaces:**
- Consumes: fixture metadata and symbol map.
- Produces: non-fixture CSV dry-run refusal until real graph/source identities are explicitly implemented.

- [ ] Write failing tests for non-fixture fixture-id contamination and `.gitignore` CSV protection.
- [ ] Implement fixture-only dry-run guard and ignore real CSV exports.
- [ ] Add Phase 15 validator and report.
- [ ] Run full verification, commit, and push.

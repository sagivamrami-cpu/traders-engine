# Phase 46 GC Real Dataset Build CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authorized GC 30m real research dataset from local Databento archives and emit a sanitized build manifest.

**Architecture:** Keep the existing `trading_system.research.gc_real_dataset_build` module as the build engine. Add a JSON schema for the manifest and a thin CLI in `tools/` that accepts local input/output paths but never writes those paths into the manifest.

**Tech Stack:** Python, pandas, pyarrow, jsonschema, pytest, YAML/JSON configs.

**Spec:** `docs/superpowers/plans/2026-09-02-phases-43-47-gc-real-dataset-to-training-start.md`

## Global Constraints

- No commit or push.
- No raw market rows, local absolute paths, secrets, or account identifiers in `agent-exchange/`.
- Dataset construction is allowed only for dataset id `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`.
- Training, model promotion, live trading, broker execution, and capital allocation remain blocked after Phase 46.
- Output rows stay under gitignored `market-data/`.

---

### Task 1: Build Manifest Contract

**Files:**
- Create: `schemas/gc_real_dataset_build_manifest.schema.json`
- Modify: `tests/research/test_gc_real_dataset_build.py`

**Interfaces:**
- Consumes: `trading_system.research.gc_real_dataset_build.GcRealDatasetBuildManifest.to_payload()`
- Produces: a schema-validated manifest payload for Phase 47 readiness.

- [ ] Write failing tests for a minimal valid build manifest and for rejecting training/model-promotion flags.
- [ ] Run `python -m pytest tests\research\test_gc_real_dataset_build.py -q` and verify failure from missing schema.
- [ ] Add `schemas/gc_real_dataset_build_manifest.schema.json`.
- [ ] Re-run the test and verify it passes.

### Task 2: Build CLI

**Files:**
- Create: `tools/build_gc_30m_real_dataset.py`
- Modify: `tests/research/test_gc_real_dataset_build.py`

**Interfaces:**
- Consumes: `build_real_dataset(...)`
- Produces: a JSON manifest at `--manifest-out`, rows under `--out-dir/<dataset-prefix>/rows.parquet`, and sanitized stdout.

- [ ] Write failing CLI help test.
- [ ] Run the CLI test and verify failure from missing script.
- [ ] Add CLI argument parsing for `--ohlcv-zip`, `--order-flow-zip`, `--identity-config`, `--identity-manifest`, `--contract`, `--out-dir`, and `--manifest-out`.
- [ ] Re-run CLI test.

### Task 3: Phase 42 Intake Link

**Files:**
- Modify: `configs/data/gc-session-calendar-construction-policy.yaml`
- Modify: `schemas/gc_session_calendar_construction_policy.schema.json`
- Modify: `trading_system/research/gc_session_calendar_construction_policy.py`
- Modify: `tests/research/test_gc_session_calendar_construction_policy.py`

**Interfaces:**
- Consumes: human/Claude delegated decision `agent-exchange/decisions/2026-09-02T130000Z-human-d2-final-session-calendar-v1-scope-overlay-transfer.md`
- Produces: `scope_amendment_decision_ref` in the construction policy report.

- [ ] Write failing policy test for `scope_amendment_decision_ref`.
- [ ] Run the policy test and verify failure.
- [ ] Add config/schema/module support.
- [ ] Re-run the policy test.

### Task 4: Verification And Handoff

**Files:**
- Create: `agent-exchange/status/2026-09-07T130000Z-codex-phase-42-review-intake-and-phase-46-build-cli-result.md`
- Update: `agent-exchange/inbox/claude-code/000_CURRENT_TASK_FOR_CLAUDE_CODE.md`

**Interfaces:**
- Consumes: local verification output.
- Produces: a review request for Claude Code after build manifest/CLI and, if the full build succeeds, a build manifest reference for Phase 47.

- [ ] Run focused unit tests.
- [ ] Run `python tools\validate_phase29.py` and `python tools\validate_phase30.py`.
- [ ] Run real build using local ZIPs when paths are available.
- [ ] Record sanitized status and route review to Claude Code.

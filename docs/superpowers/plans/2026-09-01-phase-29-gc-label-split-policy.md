# Phase 29 GC Label Split Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a sanitized, fail-closed GC label-contract and split/embargo policy candidate before real dataset construction or model training.

**Architecture:** Phase 29 creates a policy candidate that records the Codex recommendation under discussion: outcome-contract labels only, HHLL auxiliary only, chronological walk-forward split only, and purge/embargo required. The human D7/D8 packet remains unanswered until explicit decision records exist. The policy is schema-validated, emitted as sanitized JSON, chained after Phase 28 validation, and routed to Claude Code and Groq for review. It does not create labels, rows, datasets, models, features, or splits.

**Tech Stack:** Python 3, YAML, JSON Schema draft 2020-12, pytest, existing `trading_system.research` report patterns.

**Spec:** `agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md`

## Global Constraints

- Do not build a real dataset.
- Do not create labels, features, training rows, splits, models, backtests, or live-trading artifacts.
- Do not use `hhll_*` files as the training target.
- Do not use random split for time-series training or evaluation.
- Do not approve target/stop distances, horizon, thresholds, fills, costs, or graph-specific trade rules in this phase.
- Do not treat this phase as D7/D8 approval; decision records remain required.
- Do not adapt fixture trade contracts, fixture labelers, or fixture walk-forward policies to real GC.
- Keep `LABEL_CONTRACT`, `SPLIT_AND_EMBARGO_POLICY`, `DATASET_CONSTRUCTION_AUTHORIZATION`, and upstream data gates unsatisfied.
- Do not write raw market rows, secrets, local absolute paths, or large generated artifacts.
- Do not commit or push.

---

### Task 1: Policy Contract

**Files:**
- Create: `schemas/gc_label_split_policy.schema.json`
- Create: `tests/research/test_gc_label_split_policy.py`

**Interfaces:**
- Produces: JSON payload accepted by `build_gc_label_split_policy_report(...).to_payload()`.

- [ ] **Step 1: Write failing schema tests**

Create `minimal_valid_label_split_payload()` with `status=POLICY_CANDIDATE_NOT_GATE_SATISFIED`, `primary_label_family=OUTCOME_CONTRACT_LABEL`, `hhll_role=AUXILIARY_DIRECTION_LABEL_ONLY_NOT_TRAINING_TARGET`, `split_method=CHRONOLOGICAL_WALK_FORWARD_ONLY`, `random_split_allowed=false`, and construction/training booleans false.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py::test_gc_label_split_policy_schema_accepts_blocked_candidate_payload -q`

Expected: FAIL because `schemas/gc_label_split_policy.schema.json` does not exist.

- [ ] **Step 3: Add schema**

The schema must require fail-closed candidate statuses, explicit ambiguous-label exclusion, purge/embargo, 2017 damaged-window mask, blocked actions, blocked reasons, and remaining gates.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py::test_gc_label_split_policy_schema_accepts_blocked_candidate_payload -q`

Expected: PASS.

### Task 2: Config and Builder

**Files:**
- Create: `configs/research/gc-label-split-policy.yaml`
- Create: `trading_system/research/gc_label_split_policy.py`
- Modify: `tests/research/test_gc_label_split_policy.py`

**Interfaces:**
- Produces: `build_gc_label_split_policy_report(policy_path: Path, *, created_at: datetime) -> GcLabelSplitPolicyReport`.

- [ ] **Step 1: Write failing builder test**

Test that the report remains blocked, excludes HHLL from training targets, excludes same-bar ambiguous outcomes from training, blocks random split, requires embargo, applies the 2017 damaged-aggressor exclusion mask to every variant, and emits no local paths.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py -q`

Expected: FAIL because the module/config do not exist.

- [ ] **Step 3: Implement config and builder**

Use the existing report pattern: load YAML, build a deterministic payload, populate blocked reasons from unsatisfied gates, validate against schema in `to_payload()`, and never expose local absolute paths.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py -q`

Expected: PASS.

### Task 3: CLI and Phase Validator

**Files:**
- Create: `tools/validate_gc_label_split_policy.py`
- Create: `tools/validate_phase29.py`
- Create: `tests/research/test_phase29_validator.py`
- Create: `docs/implementation-reports/phase-29-gc-label-split-policy.md`

**Interfaces:**
- CLI: `python tools/validate_gc_label_split_policy.py --policy configs/research/gc-label-split-policy.yaml`
- Validator: `python tools/validate_phase29.py`

- [ ] **Step 1: Write failing validator test**

Test that `python tools/validate_phase29.py` exits successfully and prints `Phase 29 artifacts validated`.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_phase29_validator.py -q`

Expected: FAIL because `tools/validate_phase29.py` does not exist.

- [ ] **Step 3: Add CLI, validator, and report**

The validator must chain `tools/validate_phase28.py`, run Phase 29 tests, validate the schema, run the CLI, assert construction/training remain false, assert no local path leaks, and assert `LABEL_CONTRACT`/`SPLIT_AND_EMBARGO_POLICY` remain unsatisfied.

- [ ] **Step 4: Verify GREEN**

Run: `python tools/validate_phase29.py`

Expected: PASS with `Phase 29 artifacts validated`.

### Task 4: Agent Review Routing

**Files:**
- Create: `agent-exchange/inbox/claude-code/2026-09-01T175000Z-claude-code-review-phase-29-label-split-policy.md`
- Create: `agent-exchange/inbox/groq/2026-09-01T175001Z-groq-review-phase-29-label-split-policy.md`
- Create: `agent-exchange/status/2026-09-01T175002Z-codex-phase-29-implementation-result.md`

**Interfaces:**
- Reviewers must verify that Phase 29 cannot be consumed as a real label builder, split builder, dataset authorization, training readiness, or HHLL training-target approval.

- [ ] **Step 1: Write review requests and status**

Requests must include scope, forbidden assumptions, files, and verification command `python tools/validate_phase29.py`.

- [ ] **Step 2: Verify files exist**

Run `Test-Path` on the two inbox files and the status file.

Expected: all return `True`.

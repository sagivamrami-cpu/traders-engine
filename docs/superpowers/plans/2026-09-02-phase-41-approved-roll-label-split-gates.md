# Phase 41 Approved Roll Label Split Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the human-approved and Claude-accepted D5/D7/D8 decisions into enforceable GC research contract metadata while keeping dataset construction and training blocked.

**Architecture:** This phase only updates policy/config/schema/reporting gates. It does not read raw market rows, build a dataset, build labels, build splits, or train a model. The real dataset contract remains the single readiness authority.

**Tech Stack:** Python, PyYAML, jsonschema, pytest, existing `trading_system.research` validation modules.

**Spec:** `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`

## Global Constraints

- No commit or push.
- No raw market rows in `agent-exchange/`.
- No CVD or cumulative-delta features.
- No HHLL primary label.
- No random split.
- No dataset construction until readiness has no remaining gates.
- No training, model promotion, live trading, broker execution, or capital allocation.

---

### Task 1: D5 Roll Policy Gate Wiring

**Files:**
- Modify: `configs/datasets/gc-30m-real-dataset-contract.yaml`
- Modify: `schemas/gc_real_dataset_contract.schema.json`
- Modify: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- Consumes: D5 decision record `agent-exchange/decisions/2026-09-02T052002Z-human-d5-final-roll-policy-contract-identity.md`.
- Produces: contract `roll_policy.status = SATISFIED_RESEARCH_ONLY_UNDECLARED_CONTRACT_IDENTITY_V1`.

- [ ] **Step 1: Write the failing test**

Add assertions that the contract roll policy is satisfied for research only, carries the D5 decision ref, and preserves `contract_identity_status: UNDECLARED_PENDING_RESEARCH`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/research/test_gc_real_dataset_contract.py -q`

- [ ] **Step 3: Write minimal implementation**

Update the contract YAML and schema to accept the research-only roll policy and remove `ROLL_POLICY` from `required_unsatisfied_gates`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/research/test_gc_real_dataset_contract.py -q`

### Task 2: D7/D8 Label Split Policy Wiring

**Files:**
- Modify: `configs/research/gc-label-split-policy.yaml`
- Modify: `schemas/gc_label_split_policy.schema.json`
- Modify: `trading_system/research/gc_label_split_policy.py`
- Modify: `tests/research/test_gc_label_split_policy.py`
- Modify: `configs/datasets/gc-30m-real-dataset-contract.yaml`
- Modify: `schemas/gc_real_dataset_contract.schema.json`
- Modify: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- Consumes: D7 decision record `agent-exchange/decisions/2026-09-02T052004Z-human-d7-final-label-contract.md`.
- Consumes: D8 decision record `agent-exchange/decisions/2026-09-02T052005Z-human-d8-final-split-embargo-policy.md`.
- Produces: approved policy metadata for ATR(14), 1R target/stop, 8-bar horizon, chronological walk-forward, 8-bar embargo, and fold-local transforms.

- [ ] **Step 1: Write the failing test**

Add assertions that label/split policy is approved but still cannot build labels/splits until upstream dataset gates are satisfied.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py tests/research/test_gc_real_dataset_contract.py -q`

- [ ] **Step 3: Write minimal implementation**

Update policy YAML/schema/report blocked reasons and remove `LABEL_CONTRACT` and `SPLIT_AND_EMBARGO_POLICY` from the dataset-contract unsatisfied gate list.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/research/test_gc_label_split_policy.py tests/research/test_gc_real_dataset_contract.py -q`

### Task 3: Validation and Handoff

**Files:**
- Create: `docs/implementation-reports/phase-41-approved-roll-label-split-gates.md`
- Create: `agent-exchange/status/*phase-41*`
- Create: `agent-exchange/inbox/claude-code/*phase-41*`

**Interfaces:**
- Consumes: passing Phase 41 validation commands.
- Produces: Claude review request for the gate changes.

- [ ] **Step 1: Run readiness validation**

Run: `python tools/gc_pretraining_readiness.py ...`

- [ ] **Step 2: Document result**

Record remaining gates. Expected after this phase: `SESSION_CALENDAR`, `MISSING_BAR_POLICY`, `DATASET_IDENTITY`, `DATASET_CONSTRUCTION_AUTHORIZATION`, `REAL_DATASET_NOT_BUILT`.

- [ ] **Step 3: Send Claude review request**

Ask Claude Code to review that Phase 41 closes only D5/D7/D8-derived gates and keeps dataset construction/training blocked.

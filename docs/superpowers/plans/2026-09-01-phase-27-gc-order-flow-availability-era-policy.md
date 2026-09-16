# Phase 27 GC Order Flow Availability Era Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a sanitized, fail-closed GC order-flow availability-era policy candidate before any order-flow feature construction or model training.

**Architecture:** Phase 26 produced a Parquet file catalog only. Phase 27 consumes that catalog logic, splits each Parquet file range around the known damaged 2017 aggressor window, records cumulative-feature reset requirements, and keeps `ORDER_FLOW_ERA_MAP` unsatisfied until source, canonical input, row-level mask, and human authorization gates are explicit.

**Tech Stack:** Python 3, pandas, pyarrow, YAML, JSON Schema draft 2020-12, pytest, existing `trading_system.research` patterns.

**Spec:** `docs/implementation-reports/phase-26-gc-order-flow-era-map.md`

## Global Constraints

- Do not build a real dataset.
- Do not build order-flow, CVD, macro, options, or label features.
- Do not use archived `cvd` as a feature.
- Do not query vendors or external APIs.
- Do not write local absolute archive paths, secrets, raw market-data rows, or large generated artifacts.
- Keep `ORDER_FLOW_SOURCE_DECISION`, `ORDER_FLOW_ERA_MAP`, canonical input gates, and dataset construction authorization unsatisfied.
- Do not commit or push.

---

### Task 1: Availability-Era Policy Contract

**Files:**
- Create: `schemas/gc_order_flow_availability_era_policy.schema.json`
- Create: `tests/research/test_gc_order_flow_availability_era_policy.py`

**Interfaces:**
- Produces: JSON payload contract for `build_gc_order_flow_availability_era_policy(...).to_payload()`.

- [ ] **Step 1: Write failing schema tests**

```python
def test_gc_order_flow_availability_policy_schema_accepts_blocked_candidate_payload():
    payload = minimal_valid_policy_payload()
    validate_policy_payload(payload)
    assert payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_CANDIDATE_ONLY"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_schema_accepts_blocked_candidate_payload -q`

Expected: FAIL because the schema file does not exist.

- [ ] **Step 3: Add schema**

The schema must require `status=ORDER_FLOW_AVAILABILITY_POLICY_CANDIDATE_SOURCE_BLOCKED`, `zip_path=LOCAL_PATH_REDACTED`, per-file regimes, cumulative reset policy, blocked actions, and remaining gates.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/research/test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_schema_accepts_blocked_candidate_payload -q`

Expected: PASS.

### Task 2: Policy Builder

**Files:**
- Create: `trading_system/research/gc_order_flow_availability_era_policy.py`
- Modify: `tests/research/test_gc_order_flow_availability_era_policy.py`

**Interfaces:**
- Consumes: `build_gc_order_flow_era_map(zip_path, gates_path, decisions_path, created_at=...)`.
- Produces: `build_gc_order_flow_availability_era_policy(zip_path: Path, gates_path: Path, decisions_path: Path, *, created_at: datetime) -> GcOrderFlowAvailabilityEraPolicy`.

- [ ] **Step 1: Write failing builder test**

```python
def test_gc_order_flow_availability_policy_splits_known_damage_regimes_and_blocks_training(tmp_path: Path):
    zip_path = write_policy_zip(tmp_path)
    payload = build_gc_order_flow_availability_era_policy(zip_path, GATES_PATH, DECISIONS_PATH, created_at=CREATED_AT).to_payload()
    policy = payload["per_file_policies"][0]
    assert [regime["regime_id"] for regime in policy["regimes"]] == [
        "PRE_KNOWN_DAMAGE_UNVERIFIED",
        "KNOWN_DAMAGED_AGGRESSOR_WINDOW",
        "POST_KNOWN_DAMAGE_REQUIRES_PIT_RECOMPUTE",
    ]
    assert policy["allowed_for_training"] is False
    assert payload["training_allowed"] is False
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_splits_known_damage_regimes_and_blocks_training -q`

Expected: FAIL because the builder module does not exist.

- [ ] **Step 3: Implement builder**

Create a dataclass with `to_payload()`. Reuse Phase 26 catalog output, split ranges around the configured half-open damaged window, mark all regimes as non-training, require cumulative resets at file starts, damage-window boundaries, and walk-forward fold boundaries, and validate the payload against schema.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/research/test_gc_order_flow_availability_era_policy.py -q`

Expected: PASS.

### Task 3: CLI and Phase Validator

**Files:**
- Create: `tools/inspect_gc_order_flow_availability_era_policy.py`
- Create: `tools/validate_phase27.py`
- Create: `tests/research/test_phase27_validator.py`
- Create: `docs/implementation-reports/phase-27-gc-order-flow-availability-era-policy.md`

**Interfaces:**
- CLI arguments: `--zip`, `--gates`, `--decisions`.
- Validator command: `python tools/validate_phase27.py`.

- [ ] **Step 1: Write failing CLI/validator tests**

```python
def test_phase27_validator_runs_successfully():
    result = subprocess.run([sys.executable, "tools/validate_phase27.py"], cwd=ROOT, text=True, capture_output=True, check=True)
    assert "Phase 27 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/research/test_phase27_validator.py -q`

Expected: FAIL because `tools/validate_phase27.py` does not exist.

- [ ] **Step 3: Add CLI, validator, and report**

The validator must chain Phase 26 validation, run Phase 27 tests, validate schema, run the CLI on a temporary ZIP, and assert no local path leaks.

- [ ] **Step 4: Verify GREEN**

Run: `python tools/validate_phase27.py`

Expected: PASS with `Phase 27 artifacts validated`.

### Task 4: Agent Review Routing

**Files:**
- Create: `agent-exchange/inbox/claude-code/YYYY-MM-DDTHHMMSSZ-claude-code-review-phase-27-order-flow-availability-era-policy.md`
- Create: `agent-exchange/inbox/groq/YYYY-MM-DDTHHMMSSZ-groq-review-phase-27-order-flow-availability-era-policy.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-27-implementation-result.md`

**Interfaces:**
- Reviewers must verify that Phase 27 cannot be consumed as source approval, feature approval, dataset authorization, or training readiness.

- [ ] **Step 1: Write review requests and status**

Requests must include scope, forbidden assumptions, files, and verification command `python tools/validate_phase27.py`.

- [ ] **Step 2: Verify files exist**

Run: `Test-Path` for each new request/status file.

Expected: all return `True`.

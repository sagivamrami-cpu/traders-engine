# Phase 26 GC Order Flow Era Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a sanitized full-Parquet era-map profiler for the supplied GC order-flow archive before any order-flow features or real dataset construction.

**Architecture:** Phase 26 extends the Phase 23 profile-only boundary from sampled archive profiling to full Parquet era mapping. It records file role, columns, timestamp column, timezone status, row count, start/end timestamps, CVD presence, and known damaged-window overlap. It does not extract raw data, build features, create datasets, label rows, train models, or approve source readiness.

**Tech Stack:** Python 3, pandas, pyarrow, zipfile, jsonschema Draft 2020-12, pytest, existing Phase 23 order-flow profiling helpers and Phase 25 pre-training readiness gate.

**Spec:** `configs/datasets/gc-30m-real-dataset-contract.yaml`, `agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md`, `docs/implementation-reports/phase-25-gc-pretraining-readiness.md`.

## Global Constraints

- Codex remains architecture owner and final acceptance owner.
- Do not commit or push.
- Do not write secrets, API keys, raw market-data payloads, large generated artifacts, or local absolute data paths to repo files or `agent-exchange/`.
- Phase 26 may read the local order-flow ZIP for metadata and timestamp ranges only.
- Phase 26 must not query vendors, extract archives, resample bars, build features, build datasets, create labels, train models, promote models, deploy, live trade, execute broker actions, or allocate capital.
- `ORDER_FLOW_SOURCE_DECISION` remains open.
- `dataset_construction_allowed`, `training_allowed`, and `model_promotion_allowed` remain false.
- All exclusion windows use half-open UTC `[start, end)` semantics.

---

## File Structure

- Create `schemas/gc_order_flow_era_map.schema.json`: schema for sanitized era-map payload.
- Create `trading_system/research/gc_order_flow_era_map.py`: ZIP profiler that scans every Parquet entry.
- Create `tools/inspect_gc_order_flow_era_map.py`: CLI for sanitized JSON output.
- Create `tools/validate_phase26.py`: deterministic validator using temp ZIPs.
- Create `tests/research/test_gc_order_flow_era_map.py`: unit and CLI tests.
- Create `tests/research/test_phase26_validator.py`: validator smoke test.
- Create `docs/implementation-reports/phase-26-gc-order-flow-era-map.md`: report.
- Create review requests for Claude Code and Groq.

---

### Task 1: Schema and Tests

**Files:**
- Create: `schemas/gc_order_flow_era_map.schema.json`
- Test: `tests/research/test_gc_order_flow_era_map.py`

**Interfaces:**
- `validate_gc_order_flow_era_map_payload(payload: dict[str, Any]) -> None`

- [ ] **Step 1: Write failing schema test**

```python
def test_gc_order_flow_era_map_schema_accepts_profiled_blocked_payload():
    payload = minimal_valid_era_map_payload()
    validate_gc_order_flow_era_map_payload(payload)
    assert payload["status"] == "ORDER_FLOW_ERA_MAP_PROFILED_SOURCE_BLOCKED"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
```

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/research/test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_schema_accepts_profiled_blocked_payload -q
```

Expected: FAIL because schema is missing.

- [ ] **Step 3: Create schema**

Require: `report_id`, `report_version`, `mode`, `created_at`, `status`, `zip_path`, `zip_sha256`, `canonical_symbol`, `source_id`, `interval_semantics`, `known_damaged_aggressor_window`, `parquet_eras`, `order_flow_source_decision_status`, `dataset_construction_allowed`, `training_allowed`, `allowed_next_actions`, `blocked_actions`, `blocked_reasons`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
python -m pytest tests/research/test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_schema_accepts_profiled_blocked_payload -q
```

Expected: PASS.

---

### Task 2: Era-Map Profiler

**Files:**
- Create: `trading_system/research/gc_order_flow_era_map.py`
- Test: `tests/research/test_gc_order_flow_era_map.py`

**Interfaces:**
- `build_gc_order_flow_era_map(zip_path: Path, gates_path: Path, decisions_path: Path, *, created_at: datetime) -> GcOrderFlowEraMap`
- `GcOrderFlowEraMap.to_payload() -> dict[str, Any]`

- [ ] **Step 1: Write failing profiler test**

The test must create a temp ZIP with order-flow and OHLCV Parquet files, assert every Parquet file appears in `parquet_eras`, assert `cvd_present` is true only for CVD files, assert paths are redacted, and assert all approval booleans are false.

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/research/test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_profiles_every_parquet_without_leaking_paths -q
```

Expected: FAIL because module is missing.

- [ ] **Step 3: Implement profiler**

Implementation rules:
- Open ZIP read-only.
- Classify role as `ORDER_FLOW_1M`, `OHLCV_1M`, or `UNKNOWN_PARQUET`.
- Read Parquet schema and the timestamp column only; do not emit raw row values except first/last timestamp.
- Timestamp column selection: `minute` when present; otherwise last column; otherwise null.
- Timezone statuses: `UTC`, `NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE`, `UNKNOWN`.
- `status` is `ORDER_FLOW_ERA_MAP_PROFILED_SOURCE_BLOCKED` only when readable, at least one order-flow Parquet exists, and `ORDER_FLOW_SOURCE_DECISION` remains open.
- Keep `allowed_next_actions=[]`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
python -m pytest tests/research/test_gc_order_flow_era_map.py -q
```

Expected: PASS.

---

### Task 3: CLI and Validator

**Files:**
- Create: `tools/inspect_gc_order_flow_era_map.py`
- Create: `tools/validate_phase26.py`
- Create: `tests/research/test_phase26_validator.py`

**Interfaces:**
- CLI:

```bash
python tools/inspect_gc_order_flow_era_map.py --zip "<local_order_flow_zip_path>" --gates configs/data/gc-order-flow-quality-gates.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

- [ ] **Step 1: Write failing CLI and validator tests**

The CLI test must assert sanitized JSON, no absolute local path, status blocked, and every temp Parquet entry represented.

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/research/test_gc_order_flow_era_map.py tests/research/test_phase26_validator.py -q
```

Expected: FAIL until CLI and validator exist.

- [ ] **Step 3: Implement CLI and validator**

`tools/validate_phase26.py` must run `python tools/validate_phase25.py`, focused era-map tests, schema validation, temp-ZIP CLI validation, path redaction checks, and print `Phase 26 artifacts validated`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
python tools/validate_phase26.py
```

Expected: PASS.

---

## Self-Review

- Spec coverage: full-Parquet era profiling addresses the Phase 24 `ORDER_FLOW_ERA_MAP` technical blocker without approving order-flow features.
- Placeholder scan: every task has concrete files, commands, and expected results.
- Type consistency: `gc-order-flow-era-map-0.1.0`, `GC_ORDER_FLOW_ERA_MAP`, `ORDER_FLOW_ERA_MAP_PROFILED_SOURCE_BLOCKED`, and `build_gc_order_flow_era_map` are used consistently.
- Safety: all approvals and model/data construction remain blocked.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-phase-26-gc-order-flow-era-map.md`.

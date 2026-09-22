# Phase 23 GC Order Flow Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, read-only profile gate for the supplied local Databento GC order-flow archive before any order-flow feature construction, resampling, dataset build, or model training.

**Architecture:** Phase 23 mirrors the Phase 20 source-profile pattern but targets the order-flow archive shape: one-minute Parquet order-flow aggregates, one-minute OHLCV-from-ticks Parquet files, raw DBN trade ticks, and the archive README. The profiler emits sanitized metadata, measured column/timestamp/era diagnostics, and machine-readable blocked actions. It does not mark `ORDER_FLOW_SOURCE_DECISION` satisfied and does not write or extract raw market data.

**Tech Stack:** Python 3, pandas, pyarrow, zipfile, pytest, jsonschema Draft 2020-12, PyYAML, existing `trading_system.research.readiness` and data-foundation helpers.

**Spec:** `agent-exchange/reviews/2026-09-01T154500Z-groq-review-gc-order-flow-decisions.md`, `agent-exchange/reviews/2026-09-01T160500Z-claude-code-review-gc-order-flow-decisions.md`, `agent-exchange/status/2026-09-01T161500Z-codex-gc-order-flow-review-intake.md`.

## Global Constraints

- Codex remains architecture authority and final acceptance owner.
- Claude Code and Groq must be consulted for review when the Phase 23 implementation is ready.
- Do not commit or push; the human said they will handle that later.
- Do not put secrets, API keys, raw market-data payloads, large generated artifacts, or local absolute data paths in repo files or `agent-exchange/`.
- Phase 23 may read the local order-flow ZIP for metadata/profile only.
- Phase 23 must not extract the full archive, copy raw data, mutate raw data, upload data, call Databento APIs, resample a persistent dataset, build order-flow features, build candidate rows, train models, promote models, deploy, live trade, execute broker actions, or allocate capital.
- `ORDER_FLOW_SOURCE_DECISION` remains `OPEN_HUMAN_DECISION`; the supplied order-flow archive is approved only for profile-only intake.
- `OPTIONS_SOURCE_DECISION` is `DEFERRED` to v2 and must not approve or query any options parent.
- `gold_orderflow_4h.csv` and `hhll_*` files are reference-only and must not be joined into training rows, labels, feature stores, or default dataset builders.
- 2017-01-01 through 2017-05-31 is a known damaged-aggressor interval, but not the complete order-flow era policy.
- CVD and other cumulative order-flow features must be treated as path-dependent and blocked until a PIT, fold-local, era-gapped policy exists.
- 30m is a first baseline candidate only; it is not a frozen training timeframe until Phase 24 pins session, bar boundary, timestamp role, missing-bar policy, and roll policy.
- Macro features remain research-open and per-source leakage-gated; no macro feature is approved for v1 dataset construction.

---

## File Structure

- Create `configs/data/databento-gc-order-flow-source-metadata.yaml`: metadata for the local order-flow archive, with no local path.
- Create `configs/data/gc-order-flow-quality-gates.yaml`: damaged interval, cumulative-feature, 4H-reference, timeframe-candidate, and macro gates.
- Create `schemas/databento_gc_order_flow_profile.schema.json`: sanitized profile contract.
- Create `trading_system/research/databento_gc_order_flow_profile.py`: read-only ZIP profiler.
- Create `tools/inspect_databento_gc_order_flow_zip.py`: CLI that prints sanitized profile JSON.
- Create `tools/validate_phase23.py`: deterministic Phase 23 validator that uses temporary fixtures, not the real local archive.
- Create `tests/research/test_databento_gc_order_flow_profile.py`: tests for profile payload, schema validation, blocked actions, and fail-closed cases.
- Create `tests/research/test_phase23_validator.py`: validator smoke test.
- Create `docs/implementation-reports/phase-23-gc-order-flow-profile.md`: implementation report.
- Create `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-23-implementation-result.md`: result note for Codex and reviewers.
- Modify `tools/validate_phase21.py`: do not call Phase 23; Phase 23 must be separately validated.

---

### Task 1: Config and Gate Contract

**Files:**
- Create: `configs/data/databento-gc-order-flow-source-metadata.yaml`
- Create: `configs/data/gc-order-flow-quality-gates.yaml`
- Test: `tests/research/test_databento_gc_order_flow_profile.py`

**Interfaces:**
- Produces metadata consumed by `load_gc_order_flow_metadata(path: Path) -> dict[str, Any]`.
- Produces quality gates consumed by `load_gc_order_flow_quality_gates(path: Path) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing config test**

```python
def test_order_flow_configs_lock_profile_only_gates():
    metadata = yaml.safe_load((ROOT / "configs/data/databento-gc-order-flow-source-metadata.yaml").read_text())
    gates = yaml.safe_load((ROOT / "configs/data/gc-order-flow-quality-gates.yaml").read_text())

    assert metadata["source_id"] == "databento-gc-order-flow"
    assert metadata["source_status"] == "PROFILE_ONLY_NOT_SOURCE_APPROVED"
    assert metadata["canonical_symbol"] == "GC"
    assert metadata["vendor"] == "DATABENTO"
    assert "local_path" not in metadata

    assert gates["known_damaged_aggressor_window"]["start"] == "2017-01-01T00:00:00Z"
    assert gates["known_damaged_aggressor_window"]["end"] == "2017-06-01T00:00:00Z"
    assert gates["cumulative_features"]["status"] == "BLOCKED_PENDING_PIT_ERA_GAP_POLICY"
    assert gates["reference_4h_csv"]["status"] == "REFERENCE_ONLY_DO_NOT_INGEST"
    assert gates["timeframe"]["first_baseline_candidate"] == "30m"
    assert gates["timeframe"]["status"] == "RESEARCH_PARAMETER_PENDING"
    assert gates["macro_features"]["status"] == "REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE"
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_configs_lock_profile_only_gates -v
```

Expected: FAIL because the config files do not exist.

- [ ] **Step 3: Create metadata config**

Create `configs/data/databento-gc-order-flow-source-metadata.yaml`:

```yaml
version: databento-gc-order-flow-source-metadata-0.1.0
source_id: databento-gc-order-flow
source_status: PROFILE_ONLY_NOT_SOURCE_APPROVED
source_type: ORDER_FLOW_AGGREGATES_AND_RAW_TICKS
vendor: DATABENTO
dataset: GLBX.MDP3
canonical_symbol: GC
raw_symbol: GC
native_timeframe: 1m
raw_tick_format: DBN_ZST
timezone_policy: MIXED_NAIVE_UTC_AND_TZ_AWARE_UTC_REQUIRES_NORMALIZATION
source_decision_status: ORDER_FLOW_SOURCE_DECISION_OPEN
profile_only_decision_ref: agent-exchange/decisions/2026-09-01T153800Z-human-gc-order-flow-source.md
license_retention_status: REQUIRES_ORDER_FLOW_SPECIFIC_CONFIRMATION_AFTER_PROFILE
contract_identity_status: UNDECLARED_PENDING_PROFILE
allowed_use: PROFILE_ONLY
```

- [ ] **Step 4: Create quality gates config**

Create `configs/data/gc-order-flow-quality-gates.yaml`:

```yaml
version: gc-order-flow-quality-gates-0.1.0
known_damaged_aggressor_window:
  status: EXCLUDE_FROM_ORDER_FLOW_FEATURES
  start: "2017-01-01T00:00:00Z"
  end: "2017-06-01T00:00:00Z"
  reason: DAMAGED_AGGRESSOR_SIDE_DELTA
  evidence:
    - agent-exchange/decisions/2026-09-01T153801Z-human-gc-order-flow-2017-exclusion.md
cumulative_features:
  status: BLOCKED_PENDING_PIT_ERA_GAP_POLICY
  blocked_feature_families:
    - CVD
    - CUMULATIVE_DELTA
reference_4h_csv:
  status: REFERENCE_ONLY_DO_NOT_INGEST
  blocked_actions:
    - INGEST_ORDERFLOW_4H_CSV
    - JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS
    - USE_HHLL_AS_TRADE_CONTRACT_LABEL
timeframe:
  status: RESEARCH_PARAMETER_PENDING
  first_baseline_candidate: 30m
  blocked_until_decided:
    - SESSION_CALENDAR
    - BAR_BOUNDARY
    - TIMESTAMP_ROLE
    - MISSING_BAR_POLICY
    - ROLL_POLICY
macro_features:
  status: REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE
  blocked_actions:
    - JOIN_MACRO_FEATURES
    - USE_REVISED_MACRO_SERIES
```

- [ ] **Step 5: Run config test to verify GREEN**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_configs_lock_profile_only_gates -v
```

Expected: PASS.

---

### Task 2: Profile Schema and Payload Contract

**Files:**
- Create: `schemas/databento_gc_order_flow_profile.schema.json`
- Test: `tests/research/test_databento_gc_order_flow_profile.py`

**Interfaces:**
- Produces schema validated by `validate_order_flow_payload(payload: dict[str, Any]) -> None`.

- [ ] **Step 1: Write the failing schema test**

```python
def test_order_flow_profile_schema_accepts_profile_only_payload():
    payload = minimal_valid_order_flow_payload()
    validate_order_flow_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED"
    assert payload["order_flow_source_decision_status"] == "OPEN_HUMAN_DECISION"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["allowed_next_actions"] == []
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_profile_schema_accepts_profile_only_payload -v
```

Expected: FAIL because the schema does not exist.

- [ ] **Step 3: Create schema**

The schema must require:
- `profile_id`, `profile_version`, `mode`, `created_at`, `status`
- `zip_path`, `zip_sha256`, `readme_present`
- `source_id`, `vendor`, `dataset`, `canonical_symbol`, `raw_symbol`
- `order_flow_source_decision_status`, `options_source_decision_status`
- `parquet_files`, `dbn_zst_files`, `sampled_parquet_count`
- `parquet_entry_count`, `dbn_zst_entry_count`
- `one_minute_order_flow_files`, `one_minute_ohlcv_files`, `raw_tick_files`
- `columns_by_file`, `timezone_by_file`, `row_count_by_file`, `range_by_file`
- `known_damaged_aggressor_window`
- `cumulative_feature_policy_status`
- `reference_4h_csv_status`
- `timeframe_status`, `first_baseline_candidate`
- `macro_feature_status`
- `production_allowed`, `dataset_construction_allowed`, `training_allowed`
- `allowed_next_actions`, `blocked_actions`, `blocked_reasons`

Core consts:
- `profile_version`: `databento-gc-order-flow-profile-0.1.0`
- `mode`: `DATABENTO_GC_ORDER_FLOW_ZIP_PROFILE`
- `status`: `BLOCKED` or `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED`
- `zip_path`: `LOCAL_PATH_REDACTED`
- `vendor`: `DATABENTO`
- `dataset`: `GLBX.MDP3`
- `canonical_symbol`: `GC`
- `order_flow_source_decision_status`: `OPEN_HUMAN_DECISION`
- `options_source_decision_status`: `DEFERRED_TO_V2_DO_NOT_QUERY`
- `cumulative_feature_policy_status`: `BLOCKED_PENDING_PIT_ERA_GAP_POLICY`
- `reference_4h_csv_status`: `REFERENCE_ONLY_DO_NOT_INGEST`
- `timeframe_status`: `RESEARCH_PARAMETER_PENDING`
- `first_baseline_candidate`: `30m`
- `macro_feature_status`: `REQUIRES_PER_SOURCE_DECISION_AND_LEAKAGE_GATE`
- all approval booleans false
- `allowed_next_actions` maxItems 0
- `blocked_actions` contains `BUILD_ORDER_FLOW_FEATURES`, `BUILD_REAL_DATASET`, `TRAIN_PRODUCTION_MODEL`, `INGEST_ORDERFLOW_4H_CSV`, `JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS`, `JOIN_MACRO_FEATURES`, `LIVE_TRADING`, `BROKER_EXECUTION`, and `CAPITAL_ALLOCATION`.

- [ ] **Step 4: Run schema test to verify GREEN**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_profile_schema_accepts_profile_only_payload -v
```

Expected: PASS.

---

### Task 3: Read-Only Order-Flow ZIP Profiler

**Files:**
- Create: `trading_system/research/databento_gc_order_flow_profile.py`
- Test: `tests/research/test_databento_gc_order_flow_profile.py`

**Interfaces:**
- Produces `build_databento_gc_order_flow_profile(zip_path: Path, metadata_path: Path, gates_path: Path, decisions_path: Path, *, created_at: datetime, max_sample_entries: int = 5) -> DatabentoGcOrderFlowProfile`.
- Produces `DatabentoGcOrderFlowProfile.to_payload() -> dict[str, Any]`.

- [ ] **Step 1: Write failing profiler test**

```python
def test_order_flow_profile_reads_archive_shape_without_leaking_paths(tmp_path: Path):
    zip_path = write_order_flow_zip(tmp_path)
    profile = build_databento_gc_order_flow_profile(
        zip_path,
        ROOT / "configs/data/databento-gc-order-flow-source-metadata.yaml",
        ROOT / "configs/data/gc-order-flow-quality-gates.yaml",
        ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        created_at=CREATED_AT,
    )
    payload = profile.to_payload()

    validate_order_flow_payload(payload)
    assert payload["zip_path"] == "LOCAL_PATH_REDACTED"
    assert payload["readme_present"] is True
    assert payload["parquet_entry_count"] == 3
    assert payload["dbn_zst_entry_count"] == 2
    assert payload["one_minute_order_flow_files"] == ["gc/GCall_of_1m.parquet", "gc/GCext_of_1m.parquet"]
    assert payload["one_minute_ohlcv_files"] == ["gc/GCall_ohlcv_1m.parquet"]
    assert payload["raw_tick_files"] == ["gc/ticks/GC_trades_2020-01-01.dbn.zst", "gc/ticks/GC_trades_2020-04-01.dbn.zst"]
    assert payload["production_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_profile_reads_archive_shape_without_leaking_paths -v
```

Expected: FAIL because the profiler does not exist.

- [ ] **Step 3: Implement profiler**

Implementation rules:
- Open the ZIP with `zipfile.ZipFile`.
- Detect README by `gc/README.md` or any case-insensitive `readme.md`.
- Classify `.parquet` entries by filename:
  - order-flow aggregate if name contains `_of_1m.parquet`
  - OHLCV from order-flow/ticks if name contains `ohlcv`
  - unknown parquet otherwise
- Classify raw ticks as `.dbn.zst`.
- Read Parquet metadata with `pyarrow.parquet.ParquetFile` from memory.
- For each sampled Parquet, record schema names, row count, first/last value of the timestamp column or index field.
- Do not emit raw rows.
- Normalize timezone status to one of `UTC`, `NAIVE_UTC_WALL_CLOCK_REQUIRES_LOCALIZE`, or `UNKNOWN`.
- Confirm known files:
  - `GCall_of_1m.parquet` has `volume,delta,trades,cvd,minute`
  - `GCext_of_1m.parquet` has `volume,delta,trades,minute`
  - OHLCV files have `open,high,low,close,volume,minute`
- Record damaged window from `gc-order-flow-quality-gates.yaml`; do not discover it from raw rows in Phase 23 unless a bounded monthly aggregate check is added.
- Return `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED` only when the archive is readable, README exists, at least one order-flow Parquet exists, at least one raw-tick file exists, configs load, and readiness remains blocked with `ORDER_FLOW_SOURCE_DECISION` open.
- Return `BLOCKED` with reasons for unreadable ZIP, missing README, missing order-flow Parquet, missing DBN ticks, invalid configs, or readiness unexpectedly marking order-flow satisfied.

- [ ] **Step 4: Run profiler tests**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py -q
```

Expected: PASS.

---

### Task 4: CLI, Validator, and Report

**Files:**
- Create: `tools/inspect_databento_gc_order_flow_zip.py`
- Create: `tools/validate_phase23.py`
- Create: `tests/research/test_phase23_validator.py`
- Create: `docs/implementation-reports/phase-23-gc-order-flow-profile.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-23-implementation-result.md`

**Interfaces:**
- CLI:

```bash
python tools/inspect_databento_gc_order_flow_zip.py --zip "<local_order_flow_zip_path>" --metadata configs/data/databento-gc-order-flow-source-metadata.yaml --gates configs/data/gc-order-flow-quality-gates.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

- [ ] **Step 1: Write CLI and validator tests**

```python
def test_order_flow_profile_cli_outputs_sanitized_json(tmp_path: Path):
    zip_path = write_order_flow_zip(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_databento_gc_order_flow_zip.py",
            "--zip",
            str(zip_path),
            "--metadata",
            "configs/data/databento-gc-order-flow-source-metadata.yaml",
            "--gates",
            "configs/data/gc-order-flow-quality-gates.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_order_flow_payload(payload)
    assert payload["status"] == "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED"
    assert str(zip_path) not in result.stdout
    assert result.stderr == ""
```

```python
def test_phase23_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase23.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 23 artifacts validated" in result.stdout
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/research/test_databento_gc_order_flow_profile.py::test_order_flow_profile_cli_outputs_sanitized_json tests/research/test_phase23_validator.py -q
```

Expected: FAIL because the CLI and validator do not exist.

- [ ] **Step 3: Implement CLI**

The CLI must:
- require `--zip`, `--metadata`, `--gates`, and `--decisions`
- accept `--max-sample-entries`, default `5`
- print sorted, ASCII JSON to stdout
- on unexpected exception, print `{"error":"GC_ORDER_FLOW_PROFILE_FAILED","status":"BLOCKED"}` to stderr and return exit code `1`
- never print the local ZIP path or raw row values.

- [ ] **Step 4: Implement validator**

`tools/validate_phase23.py` must:
- run `python tools/validate_phase21.py`
- run `python -m pytest tests/research/test_databento_gc_order_flow_profile.py tests/research/test_phase23_validator.py -q`
- validate `schemas/databento_gc_order_flow_profile.schema.json`
- run `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- require readiness `status=BLOCKED`, `satisfied_count=5`, `open_count=2`
- require `ORDER_FLOW_SOURCE_DECISION` still open
- require `OPTIONS_SOURCE_DECISION` still open/deferred
- run the CLI against a temporary test ZIP only, not the real local archive
- print `Phase 23 artifacts validated`.

- [ ] **Step 5: Run real local archive smoke check manually**

Run locally against the supplied ZIP path only as an operator smoke check:

```bash
python tools/inspect_databento_gc_order_flow_zip.py --zip "<local_order_flow_zip_path>" --metadata configs/data/databento-gc-order-flow-source-metadata.yaml --gates configs/data/gc-order-flow-quality-gates.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

Expected for the supplied archive:
- `status` is `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED`
- `parquet_entry_count` is `5`
- `dbn_zst_entry_count` is `22`
- README is present
- `ORDER_FLOW_SOURCE_DECISION` remains open
- `training_allowed` is false
- stdout contains no local absolute path

- [ ] **Step 6: Write report and status**

The report and status must state:
- what the profile found
- which approvals remain blocked
- why 4H CSV and HHLL are reference-only
- why 30m is only a candidate
- why macro remains per-source leakage-gated
- why 2017 is a known damaged window but not complete era policy
- exact verification commands and outcomes.

---

## Self-Review

- Spec coverage: covers Groq F1-F9 and Claude C1-C6 by narrowing order-flow to profile-only, keeping readiness blocked, adding machine-readable gates, and avoiding training/timeframe/macro approval.
- Placeholder scan: no placeholder tasks remain; each task has files, interfaces, tests, commands, and expected results.
- Type consistency: `build_databento_gc_order_flow_profile`, `DatabentoGcOrderFlowProfile`, `databento_gc_order_flow_profile.schema.json`, and `ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED` are used consistently.
- Deliberate limitation: Phase 23 does not build features. Phase 24 must be a separate dataset-contract phase after this profile and external review.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-phase-23-gc-order-flow-profile.md`.

Recommended execution: inline execution in this session using TDD, then request Claude Code and Groq review of the implementation before Phase 24.

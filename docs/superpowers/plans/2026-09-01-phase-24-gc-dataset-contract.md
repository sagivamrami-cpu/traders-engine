# Phase 24 GC Dataset Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a fail-closed GC real-dataset contract before any real dataset construction, feature construction, labeling, model training, or trading action.

**Architecture:** Phase 24 adds a machine-readable contract layer between the Phase 20/23 source profiles and the existing fixture-only dataset factory. The contract records the candidate dataset recipe and all required unresolved gates, but its schema requires `dataset_construction_allowed: false`, `training_allowed: false`, and an empty `construction_authorized_by` until a future explicit human approval record exists. This phase does not create a dataset builder.

**Tech Stack:** Python 3, PyYAML, jsonschema Draft 2020-12, pytest, existing `trading_system.data_foundation.hashing`, `trading_system.data_foundation.manifests`, `trading_system.research.readiness`, and Phase 20/23 profile contracts.

**Spec:** `agent-exchange/reviews/2026-09-01T174500Z-claude-code-review-phase-24-human-dataset-decisions.md`, `agent-exchange/inbox/groq/2026-09-01T131101Z-groq-review-phase-24-human-dataset-decisions.md`, `agent-exchange/decisions/2026-09-01T153800Z-human-gc-order-flow-source.md`, `agent-exchange/decisions/2026-09-01T153801Z-human-gc-order-flow-2017-exclusion.md`, `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`, `agent-exchange/decisions/2026-09-01T153803Z-human-options-v2-deferred.md`, `agent-exchange/decisions/2026-09-01T153804Z-human-macro-features-leakage-gated.md`.

## Global Constraints

- Codex remains architecture owner and final acceptance owner.
- Do not commit or push; the human said they will handle that later.
- Do not put secrets, API keys, raw market-data payloads, large generated artifacts, or local absolute data paths in repo files or `agent-exchange/`.
- Phase 24 must not query Databento or any external vendor.
- Phase 24 must not read or print raw market-data rows.
- Phase 24 must not extract archives, resample bars, build features, create training rows, create labels, train models, promote models, deploy, live trade, execute broker actions, or allocate capital.
- `ORDER_FLOW_SOURCE_DECISION` remains open and unsatisfied.
- `OPTIONS_SOURCE_DECISION` remains deferred to v2 and must not authorize options queries or features in v1.
- 30m is a first baseline candidate only, not a frozen training timeframe.
- `gold_orderflow_4h.csv` and `hhll_*` remain reference-only and forbidden for training rows, labels, and default builders.
- Macro features are research-open but blocked until per-source licensing, `available_at`, vintage/revision, leakage, and ablation decisions exist.
- CVD and cumulative order-flow features remain blocked until a PIT, fold-local, era-gapped recomputation policy exists.
- All exclusion intervals in this contract are half-open UTC intervals: `[start, end)`.
- The 2017-01-01T00:00:00Z to 2017-06-01T00:00:00Z damaged-aggressor interval is one known exclusion, not a complete order-flow era policy.
- `era_map` is required and currently unsatisfied before any feature build.
- Any future builder must fail unless `dataset_construction_allowed` is true and `construction_authorized_by` names a future explicit human decision record.

---

## File Structure

- Create `configs/datasets/gc-30m-real-dataset-contract.yaml`: fail-closed candidate dataset contract.
- Create `schemas/gc_real_dataset_contract.schema.json`: JSON payload schema for the contract report.
- Create `trading_system/research/gc_real_dataset_contract.py`: loader, validator, payload builder, and fail-closed gate evaluation.
- Create `tools/validate_gc_real_dataset_contract.py`: CLI that validates the contract and prints sanitized JSON.
- Create `tools/validate_phase24.py`: deterministic Phase 24 validator.
- Create `tests/research/test_gc_real_dataset_contract.py`: unit and CLI tests.
- Create `tests/research/test_phase24_validator.py`: validator smoke test.
- Create `docs/implementation-reports/phase-24-gc-dataset-contract.md`: implementation report.
- Create `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-24-implementation-result.md`: status note.
- Create review requests for Claude Code and Groq after implementation.

---

### Task 1: Contract Config

**Files:**
- Create: `configs/datasets/gc-30m-real-dataset-contract.yaml`
- Test: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- Produces `load_gc_real_dataset_contract(path: Path) -> dict[str, Any]`.
- Produces a config consumed by `build_gc_real_dataset_contract_report(...)`.

- [ ] **Step 1: Write the failing config test**

```python
def test_gc_real_dataset_contract_config_is_fail_closed():
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["contract_id"] == "gc-30m-real-dataset-contract"
    assert contract["contract_version"] == "gc-real-dataset-contract-0.1.0"
    assert contract["canonical_symbol"] == "GC"
    assert contract["candidate_timeframe"] == "30m"
    assert contract["timeframe_status"] == "CANDIDATE_ONLY_NOT_FROZEN"
    assert contract["dataset_construction_allowed"] is False
    assert contract["training_allowed"] is False
    assert contract["construction_authorized_by"] == []
    assert contract["interval_semantics"] == "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE"
    assert contract["required_unsatisfied_gates"] == [
        "SESSION_CALENDAR",
        "BAR_BOUNDARY",
        "TIMESTAMP_ROLE",
        "MISSING_BAR_POLICY",
        "ROLL_POLICY",
        "ORDER_FLOW_SOURCE_DECISION",
        "ORDER_FLOW_ERA_MAP",
        "CUMULATIVE_FEATURE_POLICY",
        "LABEL_CONTRACT",
        "SPLIT_AND_EMBARGO_POLICY",
        "DATASET_CONSTRUCTION_AUTHORIZATION",
    ]
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_config_is_fail_closed -q
```

Expected: FAIL because the config does not exist.

- [ ] **Step 3: Create the fail-closed config**

Create `configs/datasets/gc-30m-real-dataset-contract.yaml` with this exact structure:

```yaml
version: gc-real-dataset-contract-config-0.1.0
contract_id: gc-30m-real-dataset-contract
contract_version: gc-real-dataset-contract-0.1.0
canonical_symbol: GC
candidate_timeframe: 30m
timeframe_status: CANDIDATE_ONLY_NOT_FROZEN
interval_semantics: HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE
source_profiles:
  historical_ohlcv_profile: schemas/databento_gc_source_profile.schema.json
  order_flow_profile: schemas/databento_gc_order_flow_profile.schema.json
source_decisions:
  ohlcv_decisions: agent-exchange/decisions/databento-gc-real-data-decisions.yaml
  order_flow_source_decision: OPEN_HUMAN_DECISION
  options_source_decision: DEFERRED_TO_V2_DO_NOT_QUERY
session_calendar:
  status: UNSATISFIED
  required_decision: CME_GLOBEX_METALS_SESSION_CALENDAR
bar_boundary:
  status: UNSATISFIED
  required_decision: UTC_FIXED_OR_SESSION_ANCHORED_WITH_DST_RULE
timestamp_role:
  status: UNSATISFIED
  required_inputs:
    ohlcv_1s: TS_EVENT_INTERVAL_START
    order_flow_minute_column: VENDOR_TIMEZONE_CONFIRMATION_REQUIRED
  phase23_dependency: timestamp_column_by_file
available_at_policy:
  status: UNSATISFIED
  default_candidate: BAR_WINDOW_END_OR_STRICTER
missing_bar_policy:
  status: UNSATISFIED
  required_scope:
    - OHLCV
    - ORDER_FLOW_VOLUME_DELTA_TRADES
    - ORDER_FLOW_CVD_FAMILY
roll_policy:
  status: UNSATISFIED
  contract_identity: UNDECLARED_PENDING_HUMAN_DECISION
order_flow_era_map:
  status: UNSATISFIED
  required_before:
    - BUILD_ORDER_FLOW_FEATURES
    - BUILD_REAL_DATASET
  known_damaged_aggressor_window:
    start: "2017-01-01T00:00:00Z"
    end: "2017-06-01T00:00:00Z"
    semantics: HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE
    status: EXCLUDE_FROM_ORDER_FLOW_FEATURES
cumulative_feature_policy:
  status: BLOCKED_PENDING_PIT_FOLD_LOCAL_ERA_GAP_POLICY
  blocked_feature_families:
    - CVD
    - CUMULATIVE_DELTA
reference_inputs:
  orderflow_4h_csv: REFERENCE_ONLY_DO_NOT_INGEST
  hhll_files: AUXILIARY_ONLY_DO_NOT_USE_AS_TRADE_CONTRACT_LABEL
macro_features:
  status: BLOCKED_PENDING_PER_SOURCE_DECISION_AND_LEAKAGE_GATE
options_features:
  status: DEFERRED_TO_V2_DO_NOT_QUERY
label_contract:
  status: UNSATISFIED
  required_decision: OUTCOME_CONTRACT_LABEL_AT_SELECTED_TIMEFRAME
split_and_embargo_policy:
  status: UNSATISFIED
  required_controls:
    - CHRONOLOGICAL_SPLIT_ONLY
    - APPLY_2017_EXCLUSION_MASK_TO_ALL_VARIANTS
    - EMBARGO_AROUND_VALIDATION_AND_TEST_WINDOWS
dataset_identity:
  status: UNSATISFIED
  required_components:
    - INPUT_ARCHIVE_SHA256S
    - CONFIG_HASHES
    - SOURCE_PROFILE_HASHES
    - DETERMINISTIC_DATASET_ID
dataset_construction_allowed: false
training_allowed: false
construction_authorized_by: []
required_unsatisfied_gates:
  - SESSION_CALENDAR
  - BAR_BOUNDARY
  - TIMESTAMP_ROLE
  - MISSING_BAR_POLICY
  - ROLL_POLICY
  - ORDER_FLOW_SOURCE_DECISION
  - ORDER_FLOW_ERA_MAP
  - CUMULATIVE_FEATURE_POLICY
  - LABEL_CONTRACT
  - SPLIT_AND_EMBARGO_POLICY
  - DATASET_CONSTRUCTION_AUTHORIZATION
blocked_actions:
  - BUILD_REAL_DATASET
  - BUILD_ORDER_FLOW_FEATURES
  - BUILD_CVD_FEATURES
  - BUILD_MACRO_FEATURES
  - QUERY_OPTIONS_DATA
  - INGEST_ORDERFLOW_4H_CSV
  - USE_HHLL_AS_TRADE_CONTRACT_LABEL
  - TRAIN_PRODUCTION_MODEL
  - MODEL_PROMOTION
  - LIVE_TRADING
  - BROKER_EXECUTION
  - CAPITAL_ALLOCATION
```

- [ ] **Step 4: Run config test to verify GREEN**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_config_is_fail_closed -q
```

Expected: PASS.

---

### Task 2: Schema Contract

**Files:**
- Create: `schemas/gc_real_dataset_contract.schema.json`
- Test: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- Produces `validate_gc_real_dataset_contract_payload(payload: dict[str, Any]) -> None`.

- [ ] **Step 1: Write the failing schema test**

```python
def test_gc_real_dataset_contract_schema_accepts_fail_closed_payload():
    payload = minimal_valid_contract_payload()
    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["construction_authorized_by"] == []
    assert "ORDER_FLOW_ERA_MAP" in payload["required_unsatisfied_gates"]
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_schema_accepts_fail_closed_payload -q
```

Expected: FAIL because the schema/module is missing.

- [ ] **Step 3: Create schema**

Schema requirements:
- `additionalProperties: false`.
- Required top-level keys:
  - `contract_report_id`, `contract_version`, `mode`, `created_at`, `status`
  - `contract_id`, `canonical_symbol`, `candidate_timeframe`, `timeframe_status`
  - `interval_semantics`, `source_decisions`, `session_calendar`, `bar_boundary`
  - `timestamp_role`, `available_at_policy`, `missing_bar_policy`, `roll_policy`
  - `order_flow_era_map`, `cumulative_feature_policy`, `reference_inputs`
  - `macro_features`, `options_features`, `label_contract`, `split_and_embargo_policy`
  - `dataset_identity`, `dataset_construction_allowed`, `training_allowed`
  - `construction_authorized_by`, `required_unsatisfied_gates`, `blocked_actions`
  - `allowed_next_actions`, `blocked_reasons`
- Consts:
  - `contract_version: gc-real-dataset-contract-0.1.0`
  - `mode: GC_REAL_DATASET_CONTRACT`
  - `status: BLOCKED`
  - `canonical_symbol: GC`
  - `candidate_timeframe: 30m`
  - `timeframe_status: CANDIDATE_ONLY_NOT_FROZEN`
  - `interval_semantics: HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE`
  - `dataset_construction_allowed: false`
  - `training_allowed: false`
  - `construction_authorized_by` maxItems 0
  - `allowed_next_actions` maxItems 0
- `required_unsatisfied_gates` must contain every item listed in Task 1.
- `blocked_actions` must contain every item listed in Task 1.

- [ ] **Step 4: Run schema test to verify GREEN**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_schema_accepts_fail_closed_payload -q
```

Expected: PASS.

---

### Task 3: Contract Loader and Report Builder

**Files:**
- Create: `trading_system/research/gc_real_dataset_contract.py`
- Test: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- `load_gc_real_dataset_contract(path: Path) -> dict[str, Any]`
- `build_gc_real_dataset_contract_report(contract_path: Path, decisions_path: Path, *, created_at: datetime) -> GcRealDatasetContractReport`
- `GcRealDatasetContractReport.to_payload() -> dict[str, Any]`
- `validate_gc_real_dataset_contract_payload(payload: dict[str, Any]) -> None`

- [ ] **Step 1: Write the failing builder test**

```python
def test_gc_real_dataset_contract_report_preserves_blocked_readiness():
    report = build_gc_real_dataset_contract_report(
        CONTRACT_PATH,
        DECISIONS_PATH,
        created_at=CREATED_AT,
    )
    payload = report.to_payload()

    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["source_decisions"]["order_flow_source_decision"] == "OPEN_HUMAN_DECISION"
    assert payload["source_decisions"]["options_source_decision"] == "DEFERRED_TO_V2_DO_NOT_QUERY"
    assert payload["order_flow_era_map"]["status"] == "UNSATISFIED"
    assert payload["timestamp_role"]["phase23_dependency"] == "timestamp_column_by_file"
    assert payload["dataset_construction_allowed"] is False
    assert payload["allowed_next_actions"] == []
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_report_preserves_blocked_readiness -q
```

Expected: FAIL because the builder does not exist.

- [ ] **Step 3: Implement loader and builder**

Implementation rules:
- Load YAML with `yaml.safe_load`.
- Refuse non-mapping YAML.
- Load readiness decisions with `load_real_data_decisions`.
- Fail closed if `ORDER_FLOW_SOURCE_DECISION` appears in the decisions YAML.
- Require `OPTIONS_SOURCE_DECISION` to be `DEFERRED`.
- Return `status: BLOCKED` in every valid Phase 24 payload.
- Compute `contract_report_id` from stable JSON fields excluding local paths.
- Preserve nested config sections verbatim only after normalizing to JSON-safe primitives.
- Never include the absolute config path or local archive path in the payload.

- [ ] **Step 4: Run builder tests**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py -q
```

Expected: PASS.

---

### Task 4: CLI and Phase Validator

**Files:**
- Create: `tools/validate_gc_real_dataset_contract.py`
- Create: `tools/validate_phase24.py`
- Create: `tests/research/test_phase24_validator.py`
- Test: `tests/research/test_gc_real_dataset_contract.py`

**Interfaces:**
- CLI:

```bash
python tools/validate_gc_real_dataset_contract.py --contract configs/datasets/gc-30m-real-dataset-contract.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

- [ ] **Step 1: Write the failing CLI test**

```python
def test_gc_real_dataset_contract_cli_outputs_sanitized_blocked_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_real_dataset_contract.py",
            "--contract",
            "configs/datasets/gc-30m-real-dataset-contract.yaml",
            "--decisions",
            "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_gc_real_dataset_contract_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""
```

- [ ] **Step 2: Write the failing Phase 24 validator test**

```python
def test_phase24_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase24.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 24 artifacts validated" in result.stdout
```

- [ ] **Step 3: Run tests to verify RED**

Run:

```bash
python -m pytest tests/research/test_gc_real_dataset_contract.py::test_gc_real_dataset_contract_cli_outputs_sanitized_blocked_json tests/research/test_phase24_validator.py -q
```

Expected: FAIL because the CLI and validator do not exist.

- [ ] **Step 4: Implement CLI**

CLI rules:
- Require `--contract` and `--decisions`.
- Print sorted ASCII JSON to stdout.
- On unexpected exception, print `{"error":"GC_REAL_DATASET_CONTRACT_VALIDATION_FAILED","status":"BLOCKED"}` to stderr and return exit code `1`.
- Never print absolute local paths.

- [ ] **Step 5: Implement Phase 24 validator**

`tools/validate_phase24.py` must:
- run `python tools/validate_phase23.py`
- run `python -m pytest tests/research/test_gc_real_dataset_contract.py -q`
- validate `schemas/gc_real_dataset_contract.schema.json`
- run the contract CLI
- require payload `status=BLOCKED`
- require `dataset_construction_allowed=false`
- require `training_allowed=false`
- require `construction_authorized_by=[]`
- require `ORDER_FLOW_SOURCE_DECISION`, `ORDER_FLOW_ERA_MAP`, `CUMULATIVE_FEATURE_POLICY`, `LABEL_CONTRACT`, and `DATASET_CONSTRUCTION_AUTHORIZATION` in `required_unsatisfied_gates`
- require `BUILD_REAL_DATASET`, `BUILD_ORDER_FLOW_FEATURES`, `BUILD_CVD_FEATURES`, `QUERY_OPTIONS_DATA`, `INGEST_ORDERFLOW_4H_CSV`, and `TRAIN_PRODUCTION_MODEL` in `blocked_actions`
- run `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- require readiness `status=BLOCKED`, `satisfied_count=5`, and `open_count=2`
- print `Phase 24 artifacts validated`.

Do not run `tests/research/test_phase24_validator.py` from inside `tools/validate_phase24.py`; that test invokes the validator and would recurse.

- [ ] **Step 6: Run validator**

Run:

```bash
python tools/validate_phase24.py
```

Expected: PASS, `Phase 24 artifacts validated`.

---

### Task 5: Documentation, Status, and Review Routing

**Files:**
- Create: `docs/implementation-reports/phase-24-gc-dataset-contract.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-24-implementation-result.md`
- Create: `agent-exchange/inbox/claude-code/YYYY-MM-DDTHHMMSSZ-claude-code-review-phase-24-dataset-contract.md`
- Create: `agent-exchange/inbox/groq/YYYY-MM-DDTHHMMSSZ-groq-review-phase-24-dataset-contract.md`

**Interfaces:**
- Claude Code and Groq consume the review requests and write to `agent-exchange/reviews/`.

- [ ] **Step 1: Write implementation report**

The report must state:
- Phase 24 is contract-only and does not construct datasets.
- 30m remains candidate-only.
- `ORDER_FLOW_SOURCE_DECISION` remains open.
- Options remain deferred to v2.
- Macro remains per-source leakage-gated.
- `era_map` is required and unsatisfied.
- Exclusion windows use half-open UTC `[start, end)` semantics.
- The 4H CSV and HHLL files remain reference-only.
- Exact verification commands and results.

- [ ] **Step 2: Write status result**

Use `agent-exchange/templates/result.md` and include:
- request/plan path
- changed files
- verification commands
- blocked actions
- remaining blockers
- no commit/push statement

- [ ] **Step 3: Route review requests**

Claude Code request:
- Ask for contract/schema/validator/test consistency review.
- Require `python tools/validate_phase24.py`.
- Ask whether the contract still blocks all dataset/training paths.

Groq request:
- Ask for leakage, contradiction, and false-readiness review.
- Require `python tools/validate_phase24.py`.
- Ask whether any missing gate should block even the contract-only skeleton.

- [ ] **Step 4: Check exchange**

Run:

```bash
python tools/watch_agent_exchange.py --once
```

Expected: the two new review requests exist in the inboxes and no result file is treated as approval.

---

## Self-Review

- Spec coverage: Claude C1 is covered by required unsatisfied `ORDER_FLOW_ERA_MAP`; C2 is handled by treating the five committed decision records as authoritative and not treating chat shorthand as a new machine approval; C3 is covered by `HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE`.
- Placeholder scan: no task uses deferred-work placeholders; each step has concrete files, commands, and expected results.
- Type consistency: `gc-real-dataset-contract-0.1.0`, `GC_REAL_DATASET_CONTRACT`, `build_gc_real_dataset_contract_report`, `validate_gc_real_dataset_contract_payload`, and `Phase 24 artifacts validated` are used consistently.
- Safety: no task reads raw rows, queries vendors, creates datasets, builds labels, trains models, promotes models, or trades.
- Open coordination: Groq's Phase 24 decision review may still add stricter gates; Codex must process it before accepting the Phase 24 implementation.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-phase-24-gc-dataset-contract.md`.

Recommended execution: inline execution in this session using TDD for Tasks 1-4, then request Claude Code and Groq review of the implementation before accepting Phase 24.

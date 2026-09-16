# Phase 20 Databento GC ZIP Source Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe source-profile gate for the purchased Databento GC one-second ZIP archive so the project can inspect and contract the real historical source before any real dataset construction or model training.

**Architecture:** Keep Phase 20 as a read-only profiler and gate over the local ZIP. It reads parquet metadata and bounded samples from the Databento archive using `pyarrow`/`pandas`, emits a sanitized source profile with schema, validates the committed GC metadata and human decisions, and records recommended downstream policies. It does not write raw extracts, resample bars, build candidate rows, train models, or approve live/broker/deployment actions.

**Tech Stack:** Python 3, pandas, pyarrow, zipfile, pytest, jsonschema Draft 2020-12, PyYAML, existing `trading_system.research.readiness` and data-foundation helpers.

**Spec:** `docs/implementation-reports/phase-19-local-only-real-source-bundle.md`, `agent-exchange/status/2026-08-31T174558Z-codex-databento-local-dataset-intake.md`, `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`.

## Global Constraints

- Codex remains architecture authority and final acceptance owner.
- Claude Code may implement scoped tasks assigned by Codex.
- Groq reviews for contradiction, hidden approval, source/proxy confusion, leakage, and unsafe paths.
- Databento GC is the first canonical real historical source; do not call it XAUUSD.
- GC-to-XAUUSD proxy use is not approved in Phase 20.
- The purchased ZIP path is supplied locally and must not be committed into configs, exchange files, schemas, reports, or test fixtures.
- Phase 20 may read ZIP/parquet metadata and bounded row samples only.
- Phase 20 must not extract the full archive, commit raw data, retain copied raw data, upload data, resample a persistent dataset, build candidate training rows, train models, promote models, deploy, live trade, execute broker actions, or allocate capital.
- The first recommended research timeframe is 4H, because the existing `hhll_` derived files are 4H and this minimizes label-alignment risk.
- The source timestamp is `ts_event` in UTC. Gold day/session policy remains a measured research decision; do not hard-code CME settle, Globex open, or UTC midnight as the final day definition in Phase 20.
- HHLL LONG/SHORT is an auxiliary direction label, not a trade-contract outcome label and not proof of edge.
- Order-flow and options decisions remain open unless the human explicitly approves or defers them in decision records.

---

## File Structure

- Create `trading_system/research/databento_gc_source_profile.py`: read-only Databento ZIP profiler.
- Create `schemas/databento_gc_source_profile.schema.json`: sanitized profile contract.
- Create `tools/inspect_databento_gc_zip.py`: CLI that prints sanitized profile JSON.
- Create `tools/validate_phase20.py`: deterministic Phase 20 validator.
- Create `tests/research/test_databento_gc_source_profile.py`: tests for profiling, redaction, schema validation, and fail-closed cases.
- Create `tests/research/test_phase20_validator.py`: validator smoke test.
- Create `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`: implementation report.
- Modify `requirements.txt`: ensure `pandas` and `pyarrow` are declared.
- Modify `configs/data/symbol-map.yaml`: add canonical `GC` mapping.
- Modify `configs/data/source-inventory.yaml`: add Databento GC source metadata as `OPEN_HUMAN_DECISION`.
- Create `configs/data/databento-gc-source-metadata.yaml`: real-source metadata for the local Databento GC archive, without an absolute raw path.

---

### Task 1: Databento GC Config and Decision Gate

**Files:**
- Modify: `requirements.txt`
- Modify: `configs/data/symbol-map.yaml`
- Modify: `configs/data/source-inventory.yaml`
- Create: `configs/data/databento-gc-source-metadata.yaml`
- Use: `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- Test: `tests/data_foundation/test_phase1_configs.py`
- Test: `tests/data_foundation/test_source_identity.py`
- Test: `tests/research/test_real_data_readiness.py`

**Interfaces:**
- Consumes: `load_real_data_decisions(path)` and `build_real_data_readiness_report(...)`.
- Produces: committed metadata that identifies Databento GC as the first real source while keeping source status open and production gates blocked.

- [ ] **Step 1: Verify dependency declarations**

Run:

```bash
python -m pip show pandas pyarrow
```

Expected: both packages are present. If missing, install them locally and add them to `requirements.txt`:

```text
pandas>=2.2
pyarrow>=25.0
```

- [ ] **Step 2: Verify GC symbol mapping**

Ensure `configs/data/symbol-map.yaml` includes:

```yaml
  - canonical_symbol: GC
    asset_class: METALS_FUTURES
    venue: DATABENTO
    raw_symbols: [GC]
    contract_policy: cme_gold_futures_research_only
```

- [ ] **Step 3: Verify source metadata**

Ensure `configs/data/databento-gc-source-metadata.yaml` exists with:

```yaml
manifest_version: raw-source-manifest-0.1.0
source_id: databento-gc-1s
source_type: OHLCV_BAR
source_status: OPEN_HUMAN_DECISION
asset_class: METALS_FUTURES
venue: DATABENTO
canonical_symbol: GC
raw_symbol: GC
timeframe: 1s
timezone: UTC
session_calendar_id: cme-globex-metals-research-pending-v1
schema_version: databento-gc-parquet-ohlcv-0.1.0
correction_policy: vendor_historical_ohlcv_preserve_ts_event
owner: Human Data Owner
human_decision_ref: agent-exchange/decisions/2026-08-31T175800Z-human-databento-gc-historical-data.md
```

- [ ] **Step 4: Verify readiness with Databento decisions**

Run:

```bash
python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

Expected: `satisfied_count` is `5`, `open_count` is `2`, `status` is `BLOCKED`, and the two missing items are `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION`.

- [ ] **Step 5: Run config and decision tests**

Run:

```bash
python -m pytest tests/data_foundation/test_phase1_configs.py tests/data_foundation/test_source_identity.py tests/research/test_real_data_readiness.py -q
```

Expected: PASS.

---

### Task 2: Read-Only ZIP Profiler

**Files:**
- Create: `trading_system/research/databento_gc_source_profile.py`
- Test: `tests/research/test_databento_gc_source_profile.py`

**Interfaces:**
- Produces:
  - `PROFILE_VERSION = "databento-gc-source-profile-0.1.0"`
  - `MODE = "DATABENTO_GC_ZIP_SOURCE_PROFILE"`
  - `build_databento_gc_source_profile(zip_path: Path, metadata_path: Path, decisions_path: Path, *, created_at: datetime, max_sample_entries: int = 3) -> DatabentoGcSourceProfile`
  - `DatabentoGcSourceProfile.to_payload() -> dict[str, Any]`

- [ ] **Step 1: Write failing profile test**

Use a temporary ZIP with two small parquet files generated during the test. Do not use or copy the real Databento archive.

```python
def test_databento_gc_profile_reads_zip_metadata_without_leaking_path(tmp_path: Path):
    zip_path = write_gc_zip(tmp_path)
    payload = build_databento_gc_source_profile(
        zip_path,
        ROOT / "configs/data/databento-gc-source-metadata.yaml",
        ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml",
        created_at=CREATED_AT,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "PROFILE_SAMPLED_DATASET_BLOCKED"
    assert payload["zip_path"] == "LOCAL_PATH_REDACTED"
    assert payload["source_id"] == "databento-gc-1s"
    assert payload["canonical_symbol"] == "GC"
    assert payload["vendor"] == "DATABENTO"
    assert payload["parquet_entry_count"] == 2
    assert payload["columns"] == ["gc_open", "gc_high", "gc_low", "gc_close", "gc_volume"]
    assert payload["time_index_name"] == "ts_event"
    assert payload["time_index_timezone"] == "UTC"
    assert payload["row_count"] == 4
    assert payload["first_observed_at"] == "2020-01-01T00:00:00Z"
    assert payload["last_observed_at"] == "2020-02-01T00:00:01Z"
    assert payload["recommended_timeframe"] == "4h"
    assert payload["hhll_label_role"] == "AUXILIARY_DIRECTION_LABEL_ONLY"
    assert payload["production_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert str(zip_path) not in json.dumps(payload, sort_keys=True)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python -m pytest tests/research/test_databento_gc_source_profile.py::test_databento_gc_profile_reads_zip_metadata_without_leaking_path -v
```

Expected: FAIL because the module and schema do not exist yet.

- [ ] **Step 3: Implement profiler**

Implement these rules:
- Use `zipfile.ZipFile` to list `.parquet` entries.
- Read at most `max_sample_entries` full parquet entries for structural checks.
- Use `pandas.read_parquet` backed by `pyarrow`.
- Require columns exactly `gc_open`, `gc_high`, `gc_low`, `gc_close`, `gc_volume`.
- Require `DatetimeIndex` named `ts_event`.
- Require timezone-aware UTC index.
- Require monotonic increasing index within each sampled file.
- Reject duplicate timestamps within each sampled file.
- Reject null OHLCV values, invalid OHLC relationships, and negative volume.
- Compute `row_count` by reading only the `gc_close` column across entries.
- Compute first/last timestamps by reading sampled edge entries; Phase 20 does not need full archive scan for timestamps because filenames are monthly and entries are sorted.
- Redact local ZIP path in payload.
- Hash the ZIP file with `sha256_file(zip_path)`; the hash is allowed in the payload.
- Set `status="PROFILE_SAMPLED_DATASET_BLOCKED"` only when bounded profiling checks pass and the Databento decision file has the five approved items from Task 1. This status is not full-archive quality certification and does not allow dry-run, resampling, dataset construction, or training.
- Set `status="BLOCKED"` for missing decisions, invalid metadata, invalid parquet shape, unreadable zip, or empty archive.

- [ ] **Step 4: Run profile tests**

Run:

```bash
python -m pytest tests/research/test_databento_gc_source_profile.py -q
```

Expected: PASS.

---

### Task 3: Schema, CLI, and Real Archive Smoke Check

**Files:**
- Create: `schemas/databento_gc_source_profile.schema.json`
- Create: `tools/inspect_databento_gc_zip.py`
- Test: `tests/research/test_databento_gc_source_profile.py`

**Interfaces:**
- Consumes: `build_databento_gc_source_profile(...)`.
- Produces: CLI:

```bash
python tools/inspect_databento_gc_zip.py --zip <local_zip_path> --metadata configs/data/databento-gc-source-metadata.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

- [ ] **Step 1: Create schema**

The schema must require:
- `profile_id`
- `profile_version`
- `mode`
- `created_at`
- `status`
- `zip_path`
- `zip_sha256`
- `source_id`
- `canonical_symbol`
- `raw_symbol`
- `vendor`
- `timeframe`
- `metadata_path`
- `decisions_path`
- `parquet_entry_count`
- `sampled_entry_count`
- `columns`
- `time_index_name`
- `time_index_timezone`
- `row_count`
- `first_observed_at`
- `last_observed_at`
- `recommended_timeframe`
- `day_session_policy_status`
- `hhll_label_role`
- `production_allowed`
- `dataset_construction_allowed`
- `training_allowed`
- `allowed_next_actions`
- `blocked_actions`
- `blocked_reasons`

Rules:
- `zip_path`, `metadata_path`, and `decisions_path` must be `LOCAL_PATH_REDACTED`.
- `profile_version` const is `databento-gc-source-profile-0.1.0`.
- `mode` const is `DATABENTO_GC_ZIP_SOURCE_PROFILE`.
- `status` enum is `BLOCKED` or `PROFILE_SAMPLED_DATASET_BLOCKED`.
- `canonical_symbol` const is `GC`.
- `vendor` const is `DATABENTO`.
- `recommended_timeframe` const is `4h`.
- `day_session_policy_status` const is `RESEARCH_DECISION_PENDING_MEASURE_FIRST`.
- `hhll_label_role` const is `AUXILIARY_DIRECTION_LABEL_ONLY`.
- `production_allowed`, `dataset_construction_allowed`, and `training_allowed` are all const `false`.
- `allowed_next_actions` maxItems is `0`.
- `blocked_actions` must contain `BUILD_REAL_DATASET`, `TRAIN_PRODUCTION_MODEL`, `CLAIM_EDGE`, `MODEL_PROMOTION`, `LIVE_TRADING`, `BROKER_EXECUTION`, `CAPITAL_ALLOCATION`, and `DEPLOYMENT`.

- [ ] **Step 2: Add CLI test**

Use the temporary test ZIP and assert:

```python
assert payload["status"] == "PROFILE_SAMPLED_DATASET_BLOCKED"
assert "LOCAL_PATH_REDACTED" in result.stdout
assert str(zip_path) not in result.stdout
```

- [ ] **Step 3: Implement CLI**

The CLI must:
- require `--zip`
- require `--metadata`
- require `--decisions`
- accept `--max-sample-entries` default `3`
- print sorted JSON to stdout
- print sanitized blocked JSON to stderr on unexpected exception

- [ ] **Step 4: Run CLI against the real local archive**

Run:

```bash
python tools/inspect_databento_gc_zip.py --zip "<local_databento_gc_zip_path>" --metadata configs/data/databento-gc-source-metadata.yaml --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
```

Expected:
- exit code 0
- `status` is `PROFILE_SAMPLED_DATASET_BLOCKED`
- `parquet_entry_count` is `195`
- `row_count` is approximately `104212803`
- `first_observed_at` starts at `2010-06-07T00:00:02Z`
- `last_observed_at` ends at `2026-08-05T23:59:49Z`
- stdout contains no absolute local path

---

### Task 4: Validator, Report, and Agent Exchange Closure

**Files:**
- Create: `tools/validate_phase20.py`
- Create: `tests/research/test_phase20_validator.py`
- Create: `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-20-implementation-status.md`

**Interfaces:**
- Consumes: Phase 20 schema, CLI, profiler, configs, decisions.
- Produces: one deterministic validator command and an implementation report.

- [ ] **Step 1: Add validator smoke test**

```python
def test_phase20_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase20.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 20 artifacts validated" in result.stdout
```

- [ ] **Step 2: Implement validator**

`tools/validate_phase20.py` must:
- run `python tools/validate_phase19.py`
- run `python -m pytest tests/research/test_databento_gc_source_profile.py tests/research/test_phase20_validator.py -q`
- validate the committed schema.
- validate readiness with `agent-exchange/decisions/databento-gc-real-data-decisions.yaml` and require `satisfied_count=5`, `open_count=2`, `status=BLOCKED`.
- run the CLI only against the temporary test ZIP created by tests, not the real archive, so CI remains deterministic.
- print `Phase 20 artifacts validated`.

- [ ] **Step 3: Write implementation report**

The report must include:
- source facts discovered from the real local ZIP inspection
- why the canonical symbol is `GC`
- why `XAUUSD` remains out of scope unless a proxy study is approved
- recommendation: first derived research timeframe is `4h`
- recommendation: day/session policy remains research-pending and must be measured
- recommendation: HHLL label is auxiliary only
- verification commands and results
- unresolved risks
- next phase

- [ ] **Step 4: Record Codex status**

Write a status result under `agent-exchange/status/` with:
- exact changed files
- verification output
- open decisions: order-flow and options
- blockers: no real dataset construction yet, no training yet
- recommended next action: Phase 21 Databento GC 4H derived bar adapter after Groq review.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q
foreach ($p in 0..20) { python "tools/validate_phase$p.py"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml
git diff --check
python tools/watch_agent_exchange.py --once
```

Expected: all tests and validators pass. Readiness remains `BLOCKED` with exactly two open decisions. No production or trading action is approved.

---

## Self-Review

- Spec coverage: Phase 20 advances the project from local bundle preparation to real Databento source profiling while preserving all dataset and training gates.
- Placeholder scan: no placeholder implementation instructions remain.
- Type consistency: `build_databento_gc_source_profile`, `DatabentoGcSourceProfile`, `databento_gc_source_profile.schema.json`, and `PROFILE_SAMPLED_DATASET_BLOCKED` are used consistently.
- Deliberate limitation: Phase 20 does not create a 4H dataset. That belongs to Phase 21 after this source profile is accepted and reviewed.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`.

Recommended execution: Claude Code implements Tasks 1-4 with tests first. Groq reviews source identity, Databento provenance, GC-vs-XAUUSD separation, HHLL label semantics, and hidden approval risks.

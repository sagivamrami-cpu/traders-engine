# Phase 1 Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deterministic data foundation for the TR Hybrid Intelligence system: raw source inventory, source hashing, timestamp/symbol/session normalization, quality and availability eras, point-in-time storage contracts, and replay reproducibility.

**Architecture:** Keep the existing content engine untouched. Add a separate `trading_system/data_foundation` package with typed Python modules, JSON schemas, YAML source contracts, fixture-only sample data, validation tooling, tests, and a Phase 1 implementation report. The package must not train models, compute trading features, generate candidates, or place orders.

**Tech Stack:** Python 3.9+, pytest, PyYAML, jsonschema, dataclasses, pathlib, hashlib, csv, zoneinfo.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- Current session version-control handling is manual: do not commit or push unless the user explicitly changes this instruction.
- No model training starts in Phase 1.
- No live trading, broker calls, order routing, or capital allocation logic is allowed.
- No real market-data vendor is assumed. Real feeds are represented as `OPEN_HUMAN_DECISION` until approved.
- Fixture data is allowed only for tests and deterministic examples; it must be visibly marked as synthetic or fixture data.
- Raw source files are immutable inputs. Normalization writes derived records and manifests, never mutates raw records.
- Every source, dataset, normalization rule, and replay output is versioned.
- Every record that participates in historical computation must carry `observed_at`, `available_at`, `source_id`, `source_version`, and `correction_status`.
- No computation may use a record with `available_at > observation_time`.
- Missing, stale, unavailable, corrected, invalid, and unknown are separate states.
- Session and symbol normalization must be deterministic and tested around boundary conditions.
- Replay of the same interval with the same raw hashes and versions must produce byte-stable manifests.
- Large raw datasets and model artifacts remain outside Git. Git may contain schemas, configs, tests, validators, small fixtures, and metadata examples.

---

## File Structure

Create or modify these files only:

- `requirements.txt`: add runtime dependency only if the implementation requires one beyond existing Phase 0 dependencies.
- `schemas/raw_source_manifest.schema.json`: contract for immutable raw source metadata.
- `schemas/dataset_manifest.schema.json`: contract for replayable derived dataset metadata.
- `configs/data/source-inventory.yaml`: approved and open source inventory.
- `configs/data/session-calendar.yaml`: exchange/session normalization rules for the first slice.
- `configs/data/symbol-map.yaml`: canonical symbol and contract mapping rules for the first slice.
- `configs/data/normalization-policy.yaml`: timestamp, correction, missing bar, and schema-version policies.
- `trading_system/__init__.py`: package marker.
- `trading_system/data_foundation/__init__.py`: data foundation package marker and public exports.
- `trading_system/data_foundation/contracts.py`: dataclasses and enums for Phase 1 records and manifests.
- `trading_system/data_foundation/manifests.py`: manifest load, validate, and stable serialization helpers.
- `trading_system/data_foundation/hashing.py`: deterministic file and row-set hashing helpers.
- `trading_system/data_foundation/normalization.py`: timestamp, symbol, and raw OHLCV row normalization.
- `trading_system/data_foundation/sessions.py`: session calendar parsing and session boundary resolution.
- `trading_system/data_foundation/availability.py`: availability interval construction and quality status assignment.
- `trading_system/data_foundation/point_in_time.py`: point-in-time query helper over normalized fixture records.
- `trading_system/data_foundation/replay.py`: deterministic replay manifest builder.
- `tools/validate_phase1.py`: validates schemas, configs, fixture replay, and manifest stability.
- `tests/data_foundation/test_phase1_schemas.py`: schema validation tests.
- `tests/data_foundation/test_phase1_configs.py`: config cross-reference tests.
- `tests/data_foundation/test_hashing.py`: deterministic hashing tests.
- `tests/data_foundation/test_normalization.py`: timestamp, symbol, and OHLCV normalization tests.
- `tests/data_foundation/test_sessions.py`: session boundary tests.
- `tests/data_foundation/test_availability.py`: missing/stale/corrected interval tests.
- `tests/data_foundation/test_point_in_time.py`: leakage prevention tests.
- `tests/data_foundation/test_replay.py`: replay byte-stability tests.
- `tests/fixtures/data_foundation/raw/ohlcv_fixture.csv`: tiny synthetic raw input.
- `tests/fixtures/data_foundation/expected/phase1_dataset_manifest.json`: expected replay manifest.
- `docs/implementation-reports/phase-1-data-foundation.md`: Phase 1 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- Phase 0 schemas except through additive tests that verify Phase 1 compatibility

---

## Data Contracts

### Raw Source Manifest

`raw_source_manifest.schema.json` must require:

- `manifest_version`
- `source_id`
- `source_type`
- `source_status`
- `asset_class`
- `venue`
- `canonical_symbol`
- `raw_symbol`
- `timeframe`
- `timezone`
- `session_calendar_id`
- `schema_version`
- `raw_file`
- `raw_file_sha256`
- `row_count`
- `first_observed_at`
- `last_observed_at`
- `ingested_at`
- `correction_policy`
- `owner`

Allowed `source_status` values:

- `APPROVED_FIXTURE`
- `OPEN_HUMAN_DECISION`
- `DISABLED`

Allowed `source_type` values:

- `OHLCV_BAR`
- `TICK`
- `ORDER_FLOW`
- `OPTIONS_CHAIN`
- `MACRO_EVENT`
- `REFERENCE_DATA`

### Dataset Manifest

`dataset_manifest.schema.json` must require:

- `dataset_id`
- `dataset_version`
- `created_at`
- `phase`
- `source_hashes`
- `normalization_policy_version`
- `session_calendar_version`
- `symbol_map_version`
- `date_ranges`
- `record_count`
- `availability_summary`
- `quality_status_counts`
- `replay_fingerprint`

Allowed `quality_status_counts` keys:

- `VALID`
- `MISSING`
- `STALE`
- `CORRECTED`
- `INVALID`
- `UNKNOWN`

---

## Implementation Tasks

### Task 1: Phase 1 Package and Fixtures

**Files:**
- Create: `trading_system/__init__.py`
- Create: `trading_system/data_foundation/__init__.py`
- Create: `trading_system/data_foundation/contracts.py`
- Create: `tests/fixtures/data_foundation/raw/ohlcv_fixture.csv`
- Create: `tests/data_foundation/test_phase1_package.py`

**Interfaces:**
- Consumes: no external data.
- Produces: importable Phase 1 package and small synthetic raw OHLCV fixture.

- [ ] **Step 1: Write the package import test**

Create `tests/data_foundation/test_phase1_package.py` with an import check for `trading_system.data_foundation`.

- [ ] **Step 2: Add synthetic fixture data**

Create `tests/fixtures/data_foundation/raw/ohlcv_fixture.csv` with columns:

```text
raw_symbol,timestamp,open,high,low,close,volume,correction_status,available_at
```

Include at least six rows:

- two valid regular-session bars.
- one missing-volume row.
- one stale row where `available_at` is delayed.
- one corrected row with `correction_status=CORRECTED`.
- one invalid row where `high < low`.

- [ ] **Step 3: Add core dataclasses**

In `contracts.py`, define:

- `QualityStatus`
- `CorrectionStatus`
- `RawBar`
- `NormalizedBar`
- `AvailabilityInterval`
- `RawSourceManifest`
- `DatasetManifest`

Use frozen dataclasses where mutation is not required.

- [ ] **Step 4: Run the package test**

Run: `python -m pytest tests/data_foundation/test_phase1_package.py -v`

Expected: test passes.

---

### Task 2: Source and Dataset Schemas

**Files:**
- Create: `schemas/raw_source_manifest.schema.json`
- Create: `schemas/dataset_manifest.schema.json`
- Create: `tests/data_foundation/test_phase1_schemas.py`

**Interfaces:**
- Consumes: JSON Schema Draft 2020-12.
- Produces: validated Phase 1 metadata contracts.

- [ ] **Step 1: Write schema tests**

Tests must validate one complete raw source manifest and one complete dataset manifest.

- [ ] **Step 2: Add negative schema tests**

Reject:

- missing `raw_file_sha256`.
- unsupported `source_status`.
- dataset manifest without `replay_fingerprint`.
- dataset manifest with `phase` other than `1`.

- [ ] **Step 3: Implement schemas**

Use `additionalProperties: false` for the top-level contracts.

- [ ] **Step 4: Run schema tests**

Run: `python -m pytest tests/data_foundation/test_phase1_schemas.py -v`

Expected: all schema tests pass.

---

### Task 3: Data Source Configuration

**Files:**
- Create: `configs/data/source-inventory.yaml`
- Create: `configs/data/session-calendar.yaml`
- Create: `configs/data/symbol-map.yaml`
- Create: `configs/data/normalization-policy.yaml`
- Create: `tests/data_foundation/test_phase1_configs.py`

**Interfaces:**
- Consumes: Phase 0 feature and label contracts for naming alignment.
- Produces: first approved fixture source and open decisions for real market data.

- [ ] **Step 1: Write config cross-reference tests**

Tests must verify:

- every approved source references an existing session calendar.
- every approved source references an existing canonical symbol.
- every source has an owner.
- real vendors are marked `OPEN_HUMAN_DECISION`.
- all config files have explicit versions.

- [ ] **Step 2: Create source inventory**

Include:

- `ohlcv-fixture-v1` with `source_status=APPROVED_FIXTURE`.
- `real-ohlcv-source` with `source_status=OPEN_HUMAN_DECISION`.
- `real-order-flow-source` with `source_status=OPEN_HUMAN_DECISION`.
- `real-options-source` with `source_status=OPEN_HUMAN_DECISION`.

- [ ] **Step 3: Create first session calendar**

Define a deterministic `us-equities-regular-v1` calendar:

- timezone `America/New_York`.
- regular session `09:30:00` to `16:00:00`.
- weekend closed days.
- explicit early-close and holiday lists as empty arrays for v1.

- [ ] **Step 4: Create first symbol map**

Define canonical symbol `TR_FIXTURE_SPY` mapped from raw symbol `SPY`.

- [ ] **Step 5: Create normalization policy**

Define:

- timestamp parsing mode.
- UTC output requirement.
- available-time requirement.
- invalid OHLC rule.
- missing volume rule.
- correction status mapping.

- [ ] **Step 6: Run config tests**

Run: `python -m pytest tests/data_foundation/test_phase1_configs.py -v`

Expected: all config tests pass.

---

### Task 4: Deterministic Hashing

**Files:**
- Create: `trading_system/data_foundation/hashing.py`
- Create: `tests/data_foundation/test_hashing.py`

**Interfaces:**
- Consumes: paths and normalized row dictionaries.
- Produces: stable SHA-256 fingerprints.

- [ ] **Step 1: Write hashing tests**

Tests must prove:

- same file content produces the same hash.
- line-ending differences are normalized only when using row-set hashing, not raw-file hashing.
- row-set hashing is stable under dictionary key order differences.
- row order changes produce a different row-set hash.

- [ ] **Step 2: Implement hashing helpers**

Implement:

- `sha256_file(path: Path) -> str`
- `stable_json_dumps(value: Any) -> str`
- `sha256_rows(rows: Sequence[Mapping[str, Any]]) -> str`

- [ ] **Step 3: Run hashing tests**

Run: `python -m pytest tests/data_foundation/test_hashing.py -v`

Expected: all hashing tests pass.

---

### Task 5: Timestamp, Symbol, and Raw Bar Normalization

**Files:**
- Create: `trading_system/data_foundation/normalization.py`
- Modify: `trading_system/data_foundation/contracts.py`
- Create: `tests/data_foundation/test_normalization.py`

**Interfaces:**
- Consumes: fixture CSV row, symbol map, normalization policy.
- Produces: `NormalizedBar` records with UTC timestamps and quality status.

- [ ] **Step 1: Write normalization tests**

Tests must verify:

- raw `SPY` maps to `TR_FIXTURE_SPY`.
- timestamps are converted to UTC.
- `available_at` is required and converted to UTC.
- `high < low` becomes `INVALID`.
- missing volume becomes `MISSING`.
- delayed availability becomes `STALE`.
- corrected rows preserve `CORRECTED`.

- [ ] **Step 2: Implement timestamp parsing**

Use `zoneinfo.ZoneInfo` and reject timezone-naive output.

- [ ] **Step 3: Implement symbol mapping**

Unknown raw symbols must raise a deterministic `UnknownSymbolError`.

- [ ] **Step 4: Implement bar normalization**

Implement `normalize_ohlcv_row(row: Mapping[str, str], policy: NormalizationPolicy, symbol_map: SymbolMap) -> NormalizedBar`.

- [ ] **Step 5: Run normalization tests**

Run: `python -m pytest tests/data_foundation/test_normalization.py -v`

Expected: all normalization tests pass.

---

### Task 6: Session Calendar Resolution

**Files:**
- Create: `trading_system/data_foundation/sessions.py`
- Modify: `trading_system/data_foundation/contracts.py`
- Create: `tests/data_foundation/test_sessions.py`

**Interfaces:**
- Consumes: normalized timestamps and session calendar config.
- Produces: session id, in-session flag, and session boundary metadata.

- [ ] **Step 1: Write session tests**

Tests must verify:

- `09:30:00 America/New_York` is in session.
- `16:00:00 America/New_York` is session close boundary.
- premarket time is out of session.
- weekend time is out of session.
- UTC conversion does not change the local session result.

- [ ] **Step 2: Implement session calendar parser**

Implement a config-backed `SessionCalendar` dataclass.

- [ ] **Step 3: Implement session resolution**

Implement `resolve_session(timestamp_utc: datetime, calendar: SessionCalendar) -> SessionState`.

- [ ] **Step 4: Run session tests**

Run: `python -m pytest tests/data_foundation/test_sessions.py -v`

Expected: all session tests pass.

---

### Task 7: Availability Era Construction

**Files:**
- Create: `trading_system/data_foundation/availability.py`
- Modify: `trading_system/data_foundation/contracts.py`
- Create: `tests/data_foundation/test_availability.py`

**Interfaces:**
- Consumes: normalized records ordered by observation time.
- Produces: availability intervals with quality status and reason codes.

- [ ] **Step 1: Write availability tests**

Tests must verify:

- consecutive valid rows merge into one `VALID` interval.
- status changes split intervals.
- stale rows create `STALE` intervals.
- invalid rows create `INVALID` intervals.
- missing rows create `MISSING` intervals.
- corrected rows create `CORRECTED` intervals and retain source provenance.

- [ ] **Step 2: Implement interval builder**

Implement `build_availability_intervals(records: Sequence[NormalizedBar]) -> list[AvailabilityInterval]`.

- [ ] **Step 3: Add deterministic ordering**

Reject input with decreasing `observed_at` values.

- [ ] **Step 4: Run availability tests**

Run: `python -m pytest tests/data_foundation/test_availability.py -v`

Expected: all availability tests pass.

---

### Task 8: Point-in-Time Query Helper

**Files:**
- Create: `trading_system/data_foundation/point_in_time.py`
- Create: `tests/data_foundation/test_point_in_time.py`

**Interfaces:**
- Consumes: normalized records and observation time.
- Produces: records that were available at that observation time.

- [ ] **Step 1: Write leakage-prevention tests**

Tests must verify:

- a record with `available_at` after `observation_time` is excluded.
- a record observed before `observation_time` but corrected after `observation_time` returns the pre-correction view.
- quality status filtering does not convert `MISSING` to zero.
- output ordering is stable by `observed_at`, `source_id`, and `raw_symbol`.

- [ ] **Step 2: Implement point-in-time filter**

Implement `records_available_at(records: Sequence[NormalizedBar], observation_time: datetime) -> list[NormalizedBar]`.

- [ ] **Step 3: Implement latest-bar lookup**

Implement `latest_bar_at(records: Sequence[NormalizedBar], symbol: str, observation_time: datetime) -> NormalizedBar | None`.

- [ ] **Step 4: Run point-in-time tests**

Run: `python -m pytest tests/data_foundation/test_point_in_time.py -v`

Expected: all point-in-time tests pass.

---

### Task 9: Replay Manifest Builder

**Files:**
- Create: `trading_system/data_foundation/replay.py`
- Create: `trading_system/data_foundation/manifests.py`
- Create: `tests/data_foundation/test_replay.py`
- Create: `tests/fixtures/data_foundation/expected/phase1_dataset_manifest.json`

**Interfaces:**
- Consumes: source inventory, fixture CSV, normalization policy, session calendar, symbol map.
- Produces: stable dataset manifest and replay fingerprint.

- [ ] **Step 1: Write replay tests**

Tests must verify:

- replaying the same fixture twice produces the same manifest.
- changing one raw input value changes the raw source hash and replay fingerprint.
- manifest includes all config versions.
- manifest counts quality statuses separately.
- manifest validates against `dataset_manifest.schema.json`.

- [ ] **Step 2: Implement manifest serialization**

Use stable JSON serialization with sorted keys and trailing newline.

- [ ] **Step 3: Implement replay builder**

Implement `build_phase1_dataset_manifest(...) -> DatasetManifest`.

- [ ] **Step 4: Add expected manifest fixture**

Store the expected output for the synthetic fixture.

- [ ] **Step 5: Run replay tests**

Run: `python -m pytest tests/data_foundation/test_replay.py -v`

Expected: all replay tests pass.

---

### Task 10: Phase 1 Validator and Report

**Files:**
- Create: `tools/validate_phase1.py`
- Create: `docs/implementation-reports/phase-1-data-foundation.md`
- Modify: `research/priority-register.yaml`

**Interfaces:**
- Consumes: all Phase 1 schemas, configs, tests, fixture data, and replay output.
- Produces: deterministic Phase 1 validation command and implementation report.

- [ ] **Step 1: Write validator tests indirectly through full test suite**

The validator must fail if:

- any Phase 1 schema is invalid.
- any required config file is missing.
- approved fixture source cannot be replayed.
- replay manifest fails schema validation.
- real market data sources are marked as approved without a concrete owner and decision record.

- [ ] **Step 2: Implement validator**

`python tools/validate_phase1.py` must:

- validate JSON schemas.
- load YAML configs.
- verify cross-references between source inventory, session calendar, and symbol map.
- hash fixture raw data.
- normalize fixture rows.
- build availability intervals.
- build and validate dataset manifest.
- compare the manifest to `tests/fixtures/data_foundation/expected/phase1_dataset_manifest.json`.

- [ ] **Step 3: Update research register**

Add Phase 1 open decisions:

- approved production OHLCV vendor.
- approved production order-flow vendor.
- approved production options vendor.
- first real symbol for vertical-slice dataset.
- first historical date range for vertical-slice dataset.

- [ ] **Step 4: Add implementation report**

The report must include:

- scope.
- files.
- test commands.
- decisions.
- unresolved risks.
- next phase recommendation.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/data_foundation -v`

Expected: all Phase 1 tests pass.

- [ ] **Step 6: Run full specification and data-foundation tests**

Run: `python -m pytest tests/specification tests/data_foundation -v`

Expected: all tests pass.

- [ ] **Step 7: Run validators**

Run:

```bash
python tools/validate_phase0.py
python tools/validate_phase1.py
```

Expected:

- `Phase 0 artifacts validated`
- `Phase 1 artifacts validated`

- [ ] **Step 8: Check worktree**

Run: `git status --short --branch`

Expected: implementation files are uncommitted in this session unless the user explicitly authorizes commit and push.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- Fixture replay produces the same dataset manifest across repeated runs.
- A modified raw fixture changes the replay fingerprint.
- Point-in-time filtering excludes records unavailable at the observation time.
- Missing, stale, corrected, invalid, and unknown statuses are represented distinctly.
- Real production data sources remain blocked as `OPEN_HUMAN_DECISION`.
- No code in `engine/`, `brand.py`, `run_daily.py`, Telegram delivery, or Notion delivery is modified.
- No model training, backtesting, broker integration, or decision policy is implemented in Phase 1.

---

## Tool Responsibilities

- **Codex:** Owns architecture, schemas, package boundaries, tests, validators, and final acceptance.
- **Claude Code:** Best assigned to isolated implementation tasks after the tests and contracts are written, especially normalization, sessions, availability, and replay helpers.
- **Groq:** Best used for fast review of config consistency, reason-code completeness, and report summaries. Groq outputs must be treated as review input, not executable authority.

---

## Human Decisions Required Before Real Data Expansion

- Production OHLCV source.
- Production order-flow source.
- Production options source.
- First real instrument or symbol for vertical-slice replay.
- First historical interval for vertical-slice replay.
- License and storage policy for raw data outside Git.

Until these are approved, Phase 1 implementation uses only synthetic fixture data and metadata contracts.

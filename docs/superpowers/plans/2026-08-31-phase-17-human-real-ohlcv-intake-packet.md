# Phase 17 Human Real OHLCV Intake Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a sanitized human intake workflow for the first real OHLCV CSV so a human can validate shape, identity, and decision-record readiness without committing raw data or approving production by implication.

**Architecture:** Add a narrow `trading_system/research/intake_packet.py` module that composes existing CSV inspection and source identity validation into a redacted JSON packet. The packet records hashes, row counts, symbols, date ranges, metadata identity status, and required human decision records, but never records raw CSV payloads or absolute local paths.

**Tech Stack:** Python dataclasses, argparse CLI, YAML metadata, JSON Schema draft 2020-12, pytest, existing `agent-exchange` workflow.

**Spec:** `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`, `docs/implementation-reports/phase-16-real-source-identity-contracts.md`, and `agent-exchange/status/2026-08-31T181000Z-codex-phase-16-acceptance.md`.

## Global Constraints

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no production dataset construction unless matching human decision records exist under `agent-exchange/decisions/`
- no real CSV payloads, secrets, broker credentials, account data, private identifiers, or absolute user paths in committed files or agent-exchange outputs
- fixture identifiers are valid only for committed fixture tests and fixture-only dry-runs
- order-flow and options may be explicitly deferred, but defer is not approval

---

## File Structure

- Create `trading_system/research/intake_packet.py`: redacted real OHLCV intake packet builder.
- Create `schemas/real_ohlcv_intake_packet.schema.json`: schema for sanitized packet output.
- Create `configs/data/real-ohlcv-source-metadata-template.yaml`: blocked real-source metadata template with sentinel values.
- Create `agent-exchange/templates/human-decision-record.md`: markdown template for human decisions, not an approval record.
- Create `tools/prepare_real_ohlcv_intake.py`: CLI that reads a local CSV and metadata YAML, then prints a sanitized packet.
- Create `tests/research/test_intake_packet.py`: unit tests for packet generation, path redaction, and blocked status.
- Create `tests/research/test_phase17_validator.py`: smoke test for validator.
- Create `tools/validate_phase17.py`: validates schema, CLI, redaction, and Phase 16 regression.
- Create `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`: implementation report.
- Modify `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`: point humans at the new template and command.

---

### Task 1: Sanitized Intake Packet Contract

**Files:**
- Create: `schemas/real_ohlcv_intake_packet.schema.json`
- Create: `trading_system/research/intake_packet.py`
- Test: `tests/research/test_intake_packet.py`

**Interfaces:**
- Consumes:
  - `inspect_local_ohlcv_csv(csv_path, metadata_inputs, policy, symbol_map, created_at=created_at)`
  - `load_source_identity_policy(path)`
  - `validate_source_identity(metadata, policy)`
- Produces:
  - `INTAKE_PACKET_VERSION = "real-ohlcv-intake-packet-0.1.0"`
  - `RealOhlcvIntakePacket`
  - `build_real_ohlcv_intake_packet(csv_path: Path, metadata_path: Path, *, created_at: datetime) -> RealOhlcvIntakePacket`

- [ ] **Step 1: Write failing tests**

```python
def test_intake_packet_payload_validates_against_schema():
    packet = build_real_ohlcv_intake_packet(
        FIXTURE_CSV,
        METADATA_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()

    validate_payload(packet)
    assert packet["packet_version"] == "real-ohlcv-intake-packet-0.1.0"
    assert packet["status"] == "BLOCKED_NEEDS_HUMAN_DECISION"


def test_intake_packet_never_outputs_local_csv_path():
    packet = build_real_ohlcv_intake_packet(
        FIXTURE_CSV,
        METADATA_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()

    serialized = json.dumps(packet, sort_keys=True)
    assert str(FIXTURE_CSV) not in serialized
    assert "C:\\\\" not in serialized
    assert "/Users/" not in serialized
    assert packet["csv_path"] == "LOCAL_PATH_REDACTED"


def test_intake_packet_does_not_mark_source_approved():
    packet = build_real_ohlcv_intake_packet(
        FIXTURE_CSV,
        METADATA_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()

    assert packet["production_allowed"] is False
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in packet["blocked_actions"]
    assert packet["source_identity"]["production_allowed"] is False
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/research/test_intake_packet.py -v`

Expected: fail because `trading_system.research.intake_packet` and the packet schema do not exist.

- [ ] **Step 3: Add schema**

The schema must require:
- `packet_id`
- `packet_version`
- `mode`
- `created_at`
- `status`
- `csv_path`
- `raw_file_sha256`
- `row_count`
- `raw_symbols`
- `first_observed_at`
- `last_observed_at`
- `inspection`
- `source_identity`
- `required_decision_records`
- `production_allowed`
- `blocked_actions`
- `blocked_reasons`

Rules:
- `packet_version` const is `real-ohlcv-intake-packet-0.1.0`.
- `mode` const is `REAL_OHLCV_INTAKE_PACKET`.
- `csv_path` const is `LOCAL_PATH_REDACTED`.
- `production_allowed` const is `false`.
- `status` enum is `BLOCKED_NEEDS_HUMAN_DECISION` or `BLOCKED_INVALID_INPUT`.

- [ ] **Step 4: Implement packet builder**

`RealOhlcvIntakePacket.to_payload()` must include only redacted path data. It may include `raw_file_sha256`, `row_count`, `raw_symbols`, and observation date range because those are derived metadata, not raw payload rows.

Blocked actions must include:
- `BUILD_PRODUCTION_TRAINING_DATASET`
- `TRAIN_PRODUCTION_MODEL`
- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`

Required decision records must include:
- `REAL_HISTORICAL_OHLCV_CSV`
- `PRODUCTION_OHLCV_VENDOR_DECISION`
- `FIRST_REAL_SYMBOL`
- `FIRST_HISTORICAL_INTERVAL`
- `RAW_DATA_STORAGE_LICENSE_APPROVAL`
- `ORDER_FLOW_SOURCE_DECISION`
- `OPTIONS_SOURCE_DECISION`

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/research/test_intake_packet.py -v`

Expected: pass.

---

### Task 2: CLI and Metadata/Decision Templates

**Files:**
- Create: `tools/prepare_real_ohlcv_intake.py`
- Create: `configs/data/real-ohlcv-source-metadata-template.yaml`
- Create: `agent-exchange/templates/human-decision-record.md`
- Test: `tests/research/test_intake_packet.py`

**Interfaces:**
- Consumes: `build_real_ohlcv_intake_packet`.
- Produces: CLI output that is schema-valid JSON and redacted.

- [ ] **Step 1: Write failing CLI test**

```python
def test_prepare_real_ohlcv_intake_cli_outputs_redacted_schema_valid_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_ohlcv_intake.py",
            "--csv",
            str(FIXTURE_CSV),
            "--metadata",
            str(METADATA_PATH),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["csv_path"] == "LOCAL_PATH_REDACTED"
    assert str(FIXTURE_CSV) not in result.stdout
```

- [ ] **Step 2: Run CLI test to verify RED**

Run: `python -m pytest tests/research/test_intake_packet.py::test_prepare_real_ohlcv_intake_cli_outputs_redacted_schema_valid_json -v`

Expected: fail because the CLI does not exist.

- [ ] **Step 3: Add real metadata template**

Use sentinel values that cannot accidentally validate as approval:

```yaml
manifest_version: raw-source-manifest-0.1.0
source_id: UNSET_REAL_SOURCE_ID
source_type: OHLCV_BAR
source_status: OPEN_HUMAN_DECISION
asset_class: UNSET_ASSET_CLASS
venue: UNSET_VENUE
canonical_symbol: UNSET_CANONICAL_SYMBOL
raw_symbol: UNSET_RAW_SYMBOL
timeframe: UNSET_TIMEFRAME
timezone: UNSET_TIMEZONE
session_calendar_id: UNSET_SESSION_CALENDAR_ID
schema_version: local-csv-ohlcv-schema-0.1.0
correction_policy: corrections_preserve_available_at
owner: Human Data Owner
human_decision_ref: agent-exchange/decisions/UNSET_HUMAN_DECISION_RECORD.md
```

- [ ] **Step 4: Add human decision markdown template**

Template path: `agent-exchange/templates/human-decision-record.md`

Required fields:
- `Approver:`
- `Created at:`
- `Scope:`
- `Decision:`
- `Evidence:`

The template must clearly state it is a template and must not be placed in `agent-exchange/decisions/` without human completion.

- [ ] **Step 5: Implement CLI**

`tools/prepare_real_ohlcv_intake.py` must:
- require `--csv`
- require `--metadata`
- print `json.dumps(packet.to_payload(), ensure_ascii=True, indent=2, sort_keys=True)`
- never print the raw local path except in argparse error output generated before packet construction

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/research/test_intake_packet.py -v`

Expected: pass.

---

### Task 3: Human Inbox Update and Phase Validator

**Files:**
- Modify: `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- Create: `tools/validate_phase17.py`
- Create: `tests/research/test_phase17_validator.py`
- Create: `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`

**Interfaces:**
- Consumes: Phase 17 CLI/schema/templates.
- Produces: one validator command for Phase 17.

- [ ] **Step 1: Write failing validator smoke test**

```python
def test_phase17_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase17.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 17 artifacts validated" in result.stdout
```

- [ ] **Step 2: Run validator test to verify RED**

Run: `python -m pytest tests/research/test_phase17_validator.py -v`

Expected: fail because `tools/validate_phase17.py` does not exist.

- [ ] **Step 3: Implement validator**

`tools/validate_phase17.py` must:
- run `python tools/validate_phase16.py`
- build a packet from the fixture CSV and fixture metadata
- validate it against `schemas/real_ohlcv_intake_packet.schema.json`
- assert `csv_path == "LOCAL_PATH_REDACTED"`
- assert no serialized packet contains `C:\\`, `/Users/`, or `tests/fixtures/data_foundation/raw/ohlcv_fixture.csv`
- run the CLI and validate its output
- assert readiness remains `BLOCKED`
- print `Phase 17 artifacts validated`

- [ ] **Step 4: Update human inbox**

Add:
- command: `python tools/prepare_real_ohlcv_intake.py --csv <local_csv_path> --metadata <metadata_yaml_path>`
- template paths:
  - `configs/data/real-ohlcv-source-metadata-template.yaml`
  - `agent-exchange/templates/human-decision-record.md`
- warning that CLI output is sanitized but still not approval.

- [ ] **Step 5: Write implementation report**

The report must include scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 6: Run verification**

Run:
- `python -m pytest tests/research/test_intake_packet.py -v`
- `python -m pytest tests/research/test_phase17_validator.py -v`
- `python tools/validate_phase16.py`
- `python tools/validate_phase17.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

Expected: all commands pass.

---

## Self-Review

- Spec coverage: covers human real OHLCV intake, sanitized output, decision templates, and no production approval.
- Placeholder scan: no unresolved placeholder markers in the plan; sentinel values in template examples intentionally begin with `UNSET_` and must remain blocked.
- Type consistency: `RealOhlcvIntakePacket` and `build_real_ohlcv_intake_packet` are defined before CLI and validator tasks consume them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`.

Recommended execution: Claude Code implements Tasks 1-3. Groq reviews the plan and implementation for path leakage, hidden approval, and real-data intake bypasses.

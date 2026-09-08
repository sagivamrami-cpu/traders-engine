# Phase 18 Real Source Onboarding Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed real-source onboarding preflight that can consume human decision records and source metadata without allowing pending real-source identity to build manifests, bundles, datasets, or models.

**Architecture:** Keep fixture dry-run behavior separate from real-source preflight. Add a narrow `trading_system/research/real_source_onboarding.py` module and CLI that validate source identity, readiness decisions, and intake packet status, then return a redacted preflight report. Existing `csv_onboarding` and `source_bundle` must reject `REAL_SOURCE_PENDING_HUMAN_DECISION` until a later phase introduces a full real-source onboarding implementation.

**Tech Stack:** Python dataclasses, argparse, YAML/JSON, JSON Schema draft 2020-12, pytest, existing `agent-exchange` workflow.

**Spec:** `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`, `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`, `agent-exchange/status/2026-08-31T193500Z-codex-phase-17-acceptance.md`.

## Global Constraints

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no production dataset construction in Phase 18
- no production model training in Phase 18
- no model promotion in Phase 18
- no raw CSV payloads, secrets, broker credentials, account identifiers, private identifiers, or absolute local paths in committed files or agent-exchange outputs
- a valid human decision record may permit preflight readiness only; it is not production approval
- `REAL_SOURCE_PENDING_HUMAN_DECISION` must not pass through fixture onboarding, source bundle validation, or dry-run paths
- order-flow and options may be explicitly `DEFERRED`, but defer is not approval

---

## File Structure

- Create `trading_system/research/real_source_onboarding.py`: redacted real-source preflight report builder.
- Create `schemas/real_source_onboarding_preflight.schema.json`: schema for the preflight report.
- Create `tools/preflight_real_source_onboarding.py`: CLI that prints sanitized preflight JSON.
- Create `tests/research/test_real_source_onboarding_preflight.py`: tests for blocked/default, decision-record, redaction, and no-onboarding behavior.
- Create `tests/research/test_phase18_validator.py`: smoke test for the Phase 18 validator.
- Create `tools/validate_phase18.py`: validates schema, CLI, Phase 17 regression, and blocked production readiness.
- Create `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`: implementation report.
- Modify `trading_system/research/intake_packet.py`: accept an optional `project_root` so tests can use temporary symbol-map and policy files without changing committed real configs.
- Modify `trading_system/data_foundation/csv_onboarding.py`: reject real-source pending identity before manifest creation.
- Modify `trading_system/research/source_bundle.py`: return schema-valid `BLOCKED` for real-source pending identity instead of trying dry-run.
- Modify tests under `tests/data_foundation/` and `tests/research/` for the new gate.

---

### Task 1: Real-Source Identity Cannot Enter Fixture Onboarding

**Files:**
- Modify: `trading_system/data_foundation/csv_onboarding.py`
- Modify: `trading_system/research/source_bundle.py`
- Test: `tests/data_foundation/test_csv_onboarding.py`
- Test: `tests/research/test_source_bundle.py`

**Interfaces:**
- Consumes:
  - `validate_source_identity(metadata, policy) -> SourceIdentityValidation`
- Produces:
  - `CsvOnboardingError("REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED")` for non-fixture real-source metadata.
  - Source bundle payload with `status="BLOCKED"` and `blocked_reasons` containing `REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED`.

- [ ] **Step 1: Write failing onboarding test**

```python
def test_real_source_pending_identity_cannot_build_raw_manifest(tmp_path: Path):
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"
    decision_path = tmp_path / "agent-exchange/decisions/example.md"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        "Approver: Human Data Owner\n"
        "Created at: 2026-08-31T20:00:00Z\n"
        "Scope: Preflight test only\n"
        "Decision: NOT_APPROVED\n"
        "Evidence: Temporary test record\n",
        encoding="utf-8",
    )

    with pytest.raises(CsvOnboardingError, match="REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED"):
        build_raw_source_manifest_for_csv(
            FIXTURE_CSV,
            metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
            project_root=tmp_path,
        )
```

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/data_foundation/test_csv_onboarding.py::test_real_source_pending_identity_cannot_build_raw_manifest -v`

Expected: FAIL because `build_raw_source_manifest_for_csv` does not accept `project_root` and allows non-`BLOCKED` identity.

- [ ] **Step 3: Implement onboarding gate**

Add optional keyword-only `project_root: Path | None = None` to `build_raw_source_manifest_for_csv`. Pass it to `validate_source_identity`. Then fail closed unless `identity.status == "FIXTURE_ONLY"`:

```python
    identity = validate_source_identity(metadata, identity_policy, project_root=project_root)
    if identity.status == "BLOCKED":
        raise CsvOnboardingError(", ".join(identity.blocked_reasons))
    if identity.status != "FIXTURE_ONLY":
        raise CsvOnboardingError("REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED")
```

- [ ] **Step 4: Write failing source bundle test**

```python
def test_real_source_pending_identity_returns_blocked_bundle(tmp_path: Path):
    metadata = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"
    decision_path = tmp_path / "agent-exchange/decisions/example.md"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        "Approver: Human Data Owner\n"
        "Created at: 2026-08-31T20:00:00Z\n"
        "Scope: Preflight test only\n"
        "Decision: NOT_APPROVED\n"
        "Evidence: Temporary test record\n",
        encoding="utf-8",
    )
    metadata_path = tmp_path / "metadata.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding="utf-8")

    payload = validate_local_source_bundle(
        FIXTURE_CSV,
        metadata_path,
        RETENTION_POLICY_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        project_root=tmp_path,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["dry_run_summary"] is None
    assert "REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED" in payload["blocked_reasons"]
```

- [ ] **Step 5: Run source bundle test to verify RED**

Run: `python -m pytest tests/research/test_source_bundle.py::test_real_source_pending_identity_returns_blocked_bundle -v`

Expected: FAIL because `validate_local_source_bundle` does not accept `project_root` and tries the existing flow.

- [ ] **Step 6: Implement source bundle fail-closed branch**

Add optional keyword-only `project_root: Path | None = None` to `validate_local_source_bundle`. Pass it to `validate_source_identity` and `build_raw_source_manifest_for_csv`. If source identity is not `FIXTURE_ONLY`, return a schema-valid `BLOCKED` bundle with:

```python
raw_source_manifest={}
dry_run_summary=None
blocked_reasons=(*source_identity.blocked_reasons, "REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED")
```

- [ ] **Step 7: Run task tests**

Run:
- `python -m pytest tests/data_foundation/test_csv_onboarding.py -v`
- `python -m pytest tests/research/test_source_bundle.py -v`

Expected: PASS.

---

### Task 2: Redacted Real-Source Preflight Report

**Files:**
- Create: `trading_system/research/real_source_onboarding.py`
- Create: `schemas/real_source_onboarding_preflight.schema.json`
- Test: `tests/research/test_real_source_onboarding_preflight.py`

**Interfaces:**
- Consumes:
  - `build_real_ohlcv_intake_packet(csv_path: Path, metadata_path: Path, created_at=datetime) -> RealOhlcvIntakePacket`
  - `load_real_data_readiness_checklist(path: Path) -> RealDataReadinessChecklist`
  - `load_real_data_decisions(path: Path) -> RealDataDecisionFile`
  - `build_real_data_readiness_report(checklist, created_at=datetime, decisions=decisions) -> RealDataReadinessReport`
- Produces:
  - `PREFLIGHT_VERSION = "real-source-onboarding-preflight-0.1.0"`
  - `RealSourceOnboardingPreflight`
  - `build_real_source_onboarding_preflight(csv_path: Path, metadata_path: Path, decisions_path: Path | None, *, created_at: datetime, project_root: Path | None = None) -> RealSourceOnboardingPreflight`
  - `build_real_ohlcv_intake_packet(csv_path: Path, metadata_path: Path, *, created_at: datetime, project_root: Path | None = None) -> RealOhlcvIntakePacket`

- [ ] **Step 1: Write failing blocked/default test**

```python
def test_preflight_blocks_without_decision_file(tmp_path: Path):
    payload = build_real_source_onboarding_preflight(
        valid_csv(tmp_path / "valid.csv"),
        ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml",
        None,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()

    validate_payload(payload)
    assert payload["preflight_version"] == "real-source-onboarding-preflight-0.1.0"
    assert payload["status"] == "BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["csv_path"] == "LOCAL_PATH_REDACTED"
    assert "MISSING_DECISIONS_FILE" in payload["blocked_reasons"]
```

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/research/test_real_source_onboarding_preflight.py::test_preflight_blocks_without_decision_file -v`

Expected: FAIL because module and schema do not exist.

- [ ] **Step 3: Add preflight schema**

The schema must require:
- `preflight_id`
- `preflight_version`
- `mode`
- `created_at`
- `status`
- `csv_path`
- `metadata_path`
- `decisions_path`
- `intake_packet`
- `readiness`
- `source_identity`
- `production_allowed`
- `allowed_next_actions`
- `blocked_actions`
- `blocked_reasons`

Rules:
- `preflight_version` const is `real-source-onboarding-preflight-0.1.0`.
- `mode` const is `REAL_SOURCE_ONBOARDING_PREFLIGHT`.
- all path fields const `LOCAL_PATH_REDACTED` or null for missing decisions.
- `production_allowed` const is `false`.
- `status` enum is `BLOCKED` or `PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED`.
- `allowed_next_actions` must stay empty in Phase 18; this phase is a report-only
  preflight and must not advertise CLIs that the same phase still blocks.
- `blocked_actions` must include production dataset, training, model promotion, live trading, broker execution, and capital allocation.

- [ ] **Step 4: Add project-root support to the intake packet**

Modify `build_real_ohlcv_intake_packet` to accept `project_root: Path | None = None`.
Use:

```python
root = ROOT if project_root is None else project_root
normalization_policy = load_normalization_policy(root / "configs/data/normalization-policy.yaml")
symbol_map = load_symbol_map(root / "configs/data/symbol-map.yaml")
identity_policy = load_source_identity_policy(root / "configs/data/source-identity-policy.yaml")
source_identity = validate_source_identity(metadata, identity_policy, project_root=root)
```

Existing callers can omit the argument.

- [ ] **Step 5: Implement blocked/default preflight**

`build_real_source_onboarding_preflight` must:
- build the Phase 17 intake packet.
- if `decisions_path is None`, skip loading decisions and set readiness from the checklist only.
- include only redacted paths in `to_payload`.
- set `status="BLOCKED"` when intake status is not `BLOCKED_NEEDS_HUMAN_DECISION`,
  decisions are absent/invalid, or any required preflight decision is missing or
  mismatched.
- do not treat overall readiness `BLOCKED` as a preflight failure by itself;
  production readiness must remain blocked in this phase.

- [ ] **Step 6: Write failing positive preflight test with temporary human records**

```python
def test_preflight_records_present_keeps_production_and_onboarding_blocked(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path = write_real_source_fixture(tmp_path)

    payload = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        project_root=project_root,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert payload["readiness"]["status"] == "BLOCKED"
```

The helper must create:
- matching markdown records under `tmp_path/agent-exchange/decisions/`; YAML
  `APPROVED` entries must cite records with inline `Decision: APPROVED`, and
  YAML `DEFERRED` entries must cite records with inline `Decision: DEFERRED`.
- a decisions YAML under `tmp_path/agent-exchange/decisions/decisions.yaml`.
- all seven checklist items, with `APPROVED` for OHLCV/source/symbol/interval/storage and `DEFERRED` for order-flow/options.
- metadata with `source_id="real-ohlcv-spy-1m"`, `canonical_symbol="SPY.US"`, `raw_symbol="SPY"`, and `human_decision_ref="agent-exchange/decisions/source.md"`.
- `tmp_path/configs/data/normalization-policy.yaml`, `tmp_path/configs/data/source-identity-policy.yaml`, and `tmp_path/configs/research/real-data-readiness-checklist.yaml` copied from the repository.
- `tmp_path/configs/data/symbol-map.yaml` with a temporary `SPY.US` mapping for raw symbol `SPY`; do not modify committed `configs/data/symbol-map.yaml`.

- [ ] **Step 7: Run positive test to verify RED**

Run: `python -m pytest tests/research/test_real_source_onboarding_preflight.py::test_preflight_records_present_keeps_production_and_onboarding_blocked -v`

Expected: FAIL until the module supports `project_root`, temporary symbol maps, and valid temporary decision records.

- [ ] **Step 8: Implement positive preflight**

When `project_root` is provided, use it for decision-record resolution, intake
policy loading, and readiness checklist loading. Do not mutate repository
configs. Positive preflight is allowed only when the temporary test root
contains a real-source symbol map and all required human decision records are
valid. Phase 18 must still keep `allowed_next_actions` empty and leave real
manifest/bundle preparation to a later phase.

- [ ] **Step 9: Run task tests**

Run: `python -m pytest tests/research/test_real_source_onboarding_preflight.py -v`

Expected: PASS.

---

### Task 3: CLI, Validator, Report, and Routing Closure

**Files:**
- Create: `tools/preflight_real_source_onboarding.py`
- Create: `tools/validate_phase18.py`
- Create: `tests/research/test_phase18_validator.py`
- Create: `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`
- Modify: `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`

**Interfaces:**
- Consumes: `build_real_source_onboarding_preflight`.
- Produces: CLI output that is schema-valid, redacted, and never grants production approval.

- [ ] **Step 1: Write failing CLI test**

```python
def test_preflight_cli_outputs_redacted_blocked_json(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_real_source_onboarding.py",
            "--csv",
            str(valid_csv(tmp_path / "valid.csv")),
            "--metadata",
            "configs/data/real-ohlcv-source-metadata-template.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(tmp_path) not in result.stdout
```

- [ ] **Step 2: Implement CLI**

`tools/preflight_real_source_onboarding.py` must:
- require `--csv`
- require `--metadata`
- accept optional `--decisions`
- print `json.dumps(preflight.to_payload(), ensure_ascii=True, indent=2, sort_keys=True)`
- catch exceptions and print sanitized JSON to stderr with `csv_path`, `metadata_path`, and `decisions_path` redacted.

- [ ] **Step 3: Write failing validator smoke test**

```python
def test_phase18_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase18.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 18 artifacts validated" in result.stdout
```

- [ ] **Step 4: Implement validator**

`tools/validate_phase18.py` must:
- run `python tools/validate_phase17.py`
- run focused Phase 18 tests
- run CLI blocked/default scenario and validate schema
- assert serialized CLI output contains no absolute CSV, metadata, decisions, `C:\`, or `/Users/` paths
- assert default readiness remains `BLOCKED`
- print `Phase 18 artifacts validated`

- [ ] **Step 5: Update human inbox**

Add:
- `python tools/preflight_real_source_onboarding.py --csv <local_csv_path> --metadata <metadata_yaml_path> --decisions <decisions_yaml_path>`
- explicit warning: Phase 18 preflight is report-only; it does not permit local
  manifest/bundle preparation, production dataset construction, or training.

- [ ] **Step 6: Write implementation report**

The report must include scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 7: Run verification**

Run:
- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_real_source_onboarding_preflight.py tests/research/test_phase18_validator.py -v`
- `python tools/validate_phase17.py`
- `python tools/validate_phase18.py`
- `python tools/real_data_readiness.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `git diff --check`

Expected: all commands pass, readiness remains `BLOCKED`, and no production action is approved.

---

## Self-Review

- Spec coverage: covers the Phase 17 next step: consume completed human decision records and define a guarded real-source onboarding path while keeping production dataset/model gates closed.
- Placeholder scan: no implementation placeholder is required to understand the work; `UNSET_` appears only as intentional blocked sentinel input.
- Type consistency: `build_real_source_onboarding_preflight`, `RealSourceOnboardingPreflight`, `PREFLIGHT_VERSION`, and CLI names are defined before later tasks consume them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-31-phase-18-real-source-onboarding-preflight.md`.

Recommended execution: Claude Code implements Tasks 1-3 with tests first. Groq reviews the plan and implementation for hidden approval, local path leakage, decision-record bypasses, fixture leakage, and production gate bypasses.

# Phase 16 Real Source Identity Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit contracts for non-fixture real-source identity so local CSV intake can progress toward approved OHLCV-only research without fixture leakage or hidden production approval.

**Architecture:** Keep identity validation in `trading_system/data_foundation` and call it before manifest, bundle, and dry-run outputs. The contract separates fixture-only metadata, human-decision-backed real metadata, and explicit OHLCV-only deferrals for order-flow/options so source identity can be validated without approving production training.

**Tech Stack:** Python dataclasses, YAML config, JSON Schema, pytest, jsonschema, existing `agent-exchange` workflow.

**Spec:** `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`, `docs/implementation-reports/phase-15-real-data-safety-hardening.md`, and `agent-exchange/status/2026-08-31T170000Z-codex-phase-15-acceptance.md`.

## Global Constraints

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no production dataset construction unless matching human decision records exist under `agent-exchange/decisions/`
- no real CSV payloads, secrets, broker credentials, account data, or absolute user paths in committed files
- fixture identifiers are valid only for committed fixture tests and fixture-only dry-runs
- order-flow and options may be explicitly deferred, but defer is not approval

---

## File Structure

- Create `trading_system/data_foundation/source_identity.py`: source identity policy loader and metadata validator.
- Create `configs/data/source-identity-policy.yaml`: allowed fixture prefixes, real-source required fields, forbidden fixture ids, and allowed deferred producer decisions.
- Create `schemas/source_identity_policy.schema.json`: schema for the new policy file.
- Modify `trading_system/data_foundation/csv_onboarding.py`: validate source identity before raw manifest emission.
- Modify `trading_system/research/source_bundle.py`: validate source identity before bundle validation and include identity result in payload.
- Modify `trading_system/research/offline_dry_run.py`: replace the fixture-only guard with policy-backed identity validation.
- Modify `schemas/source_bundle_validation.schema.json`: add `source_identity`.
- Modify `configs/data/local-csv-onboarding-template.yaml`: keep it fixture-only and add explicit fixture mode marker if needed.
- Create `tests/data_foundation/test_source_identity.py`: unit coverage for policy loading and identity validation.
- Modify `tests/data_foundation/test_csv_onboarding.py`: enforce manifest validation rejects fixture ids outside fixture mode.
- Modify `tests/research/test_source_bundle.py`: enforce bundle payload includes identity status and remains dry-run only.
- Modify `tests/research/test_offline_dry_run.py`: enforce non-fixture metadata cannot use fixture graph/dataset identities.
- Create `tools/validate_phase16.py`: end-to-end validation for identity contracts.
- Create `docs/implementation-reports/phase-16-real-source-identity-contracts.md`: implementation report.

---

### Task 1: Source Identity Policy Contract

**Files:**
- Create: `configs/data/source-identity-policy.yaml`
- Create: `schemas/source_identity_policy.schema.json`
- Create: `trading_system/data_foundation/source_identity.py`
- Test: `tests/data_foundation/test_source_identity.py`

**Interfaces:**
- Consumes: metadata mapping from local CSV onboarding template.
- Produces:
  - `SourceIdentityPolicy`
  - `SourceIdentityValidation`
  - `load_source_identity_policy(path: Path) -> SourceIdentityPolicy`
  - `validate_source_identity(metadata: Mapping[str, Any], policy: SourceIdentityPolicy) -> SourceIdentityValidation`

- [ ] **Step 1: Write failing tests**

```python
def test_fixture_identity_is_allowed_only_in_fixture_mode():
    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(fixture_metadata(), policy)

    assert result.status == "FIXTURE_ONLY"
    assert result.production_allowed is False
    assert "PRODUCTION_DATASET_CONSTRUCTION" in result.blocked_actions


def test_real_source_rejects_fixture_identifiers():
    metadata = fixture_metadata()
    metadata["source_status"] = "OPEN_HUMAN_DECISION"
    metadata["source_id"] = "vendor-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "TR_FIXTURE_SPY"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE" in result.blocked_reasons


def test_real_source_requires_human_decision_reference():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["raw_symbol"] = "SPY"
    metadata.pop("human_decision_ref", None)

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "MISSING_HUMAN_DECISION_REF" in result.blocked_reasons
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/data_foundation/test_source_identity.py -v`

Expected: fail because `source_identity.py` and the policy schema do not exist yet.

- [ ] **Step 3: Add the policy config**

```yaml
version: source-identity-policy-0.1.0
fixture_mode:
  source_ids:
    - local-csv-ohlcv-fixture
  canonical_symbols:
    - TR_FIXTURE_SPY
  graph_ids:
    - fixture-candidate-graph-v1
  dataset_ids:
    - fixture-candidate-dataset
real_source:
  required_metadata_fields:
    - source_id
    - source_type
    - source_status
    - asset_class
    - venue
    - canonical_symbol
    - raw_symbol
    - timeframe
    - timezone
    - session_calendar_id
    - schema_version
    - correction_policy
    - owner
    - human_decision_ref
  allowed_source_statuses:
    - OPEN_HUMAN_DECISION
  forbidden_identifier_prefixes:
    - fixture
    - test-fixture
  forbidden_identifier_fragments:
    - fixture
allowed_deferred_producers:
  - ORDER_FLOW
  - OPTIONS
blocked_actions:
  - PRODUCTION_DATASET_CONSTRUCTION
  - TRAIN_PRODUCTION_MODEL
  - MODEL_PROMOTION
  - LIVE_TRADING
  - BROKER_EXECUTION
  - CAPITAL_ALLOCATION
```

- [ ] **Step 4: Add the policy schema**

The schema must require all top-level keys listed in the YAML above and must enforce non-empty arrays for `fixture_mode.source_ids`, `fixture_mode.canonical_symbols`, `real_source.required_metadata_fields`, and `blocked_actions`.

- [ ] **Step 5: Implement source identity validation**

```python
@dataclass(frozen=True)
class SourceIdentityValidation:
    status: str
    source_id: str
    canonical_symbol: str
    mode: str
    production_allowed: bool
    blocked_actions: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_id": self.source_id,
            "canonical_symbol": self.canonical_symbol,
            "mode": self.mode,
            "production_allowed": self.production_allowed,
            "blocked_actions": list(self.blocked_actions),
            "blocked_reasons": list(self.blocked_reasons),
        }
```

Rules:
- If `source_id` and `canonical_symbol` match fixture policy values, return `FIXTURE_ONLY`.
- If any real-source identifier uses fixture-only canonical symbol or fixture fragments, return `BLOCKED`.
- If required real-source metadata fields are missing or blank, return `BLOCKED`.
- If `human_decision_ref` is missing, blank, or outside `agent-exchange/decisions/`, return `BLOCKED`.
- No identity validation result may set `production_allowed=True` in Phase 16.

- [ ] **Step 6: Run unit tests**

Run: `python -m pytest tests/data_foundation/test_source_identity.py -v`

Expected: pass.

---

### Task 2: Apply Identity Validation Before Manifest and Bundle Outputs

**Files:**
- Modify: `trading_system/data_foundation/csv_onboarding.py`
- Modify: `trading_system/research/source_bundle.py`
- Modify: `schemas/source_bundle_validation.schema.json`
- Test: `tests/data_foundation/test_csv_onboarding.py`
- Test: `tests/research/test_source_bundle.py`

**Interfaces:**
- Consumes: `validate_source_identity(metadata, policy)`.
- Produces: manifest/bundle paths that fail closed on invalid identity.

- [ ] **Step 1: Write failing onboarding test**

```python
def test_onboarding_rejects_real_metadata_with_fixture_canonical_symbol(tmp_path: Path):
    bad_metadata = metadata()
    bad_metadata["source_id"] = "real-ohlcv-spy-1m"
    bad_metadata["canonical_symbol"] = "TR_FIXTURE_SPY"

    with pytest.raises(CsvOnboardingError, match="FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE"):
        build_raw_source_manifest_for_csv(
            FIXTURE_CSV,
            bad_metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        )
```

- [ ] **Step 2: Write failing source bundle test**

```python
def test_source_bundle_payload_includes_identity_validation():
    payload = bundle().to_payload()

    assert payload["source_identity"]["status"] == "FIXTURE_ONLY"
    assert payload["source_identity"]["production_allowed"] is False
    assert "PRODUCTION_DATASET_CONSTRUCTION" in payload["source_identity"]["blocked_actions"]
```

- [ ] **Step 3: Run tests to verify RED**

Run:
- `python -m pytest tests/data_foundation/test_csv_onboarding.py::test_onboarding_rejects_real_metadata_with_fixture_canonical_symbol -v`
- `python -m pytest tests/research/test_source_bundle.py::test_source_bundle_payload_includes_identity_validation -v`

Expected: fail because onboarding and bundle validation do not call source identity validation yet.

- [ ] **Step 4: Wire identity validation into onboarding**

In `build_raw_source_manifest_for_csv`, load `configs/data/source-identity-policy.yaml`, validate metadata, and raise `CsvOnboardingError(", ".join(result.blocked_reasons))` when the identity result is `BLOCKED`.

- [ ] **Step 5: Wire identity validation into bundle validation**

In `SourceBundleValidation`, add `source_identity: SourceIdentityValidation` and include `source_identity.to_payload()` in `to_payload()`. In `validate_local_source_bundle`, evaluate identity before raw manifest construction and return `BLOCKED` if identity status is `BLOCKED`.

- [ ] **Step 6: Update source bundle schema**

Add required `source_identity` object with:
- `status`
- `source_id`
- `canonical_symbol`
- `mode`
- `production_allowed`
- `blocked_actions`
- `blocked_reasons`

- [ ] **Step 7: Run tests**

Run:
- `python -m pytest tests/data_foundation/test_csv_onboarding.py -v`
- `python -m pytest tests/research/test_source_bundle.py -v`

Expected: pass.

---

### Task 3: Replace Fixture-Only Dry-Run Guard With Identity Contract

**Files:**
- Modify: `trading_system/research/offline_dry_run.py`
- Modify: `tools/run_local_csv_dry_run.py`
- Test: `tests/research/test_offline_dry_run.py`

**Interfaces:**
- Consumes: `SourceIdentityValidation`.
- Produces: dry-run output that remains fixture-only unless a later phase creates a real-source research path.

- [ ] **Step 1: Write failing tests**

```python
def test_dry_run_rejects_real_source_until_real_research_path_exists():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"

    with pytest.raises(ValueError, match="real-source dry-run path is not implemented"):
        build_local_csv_research_dry_run(
            FIXTURE_CSV,
            metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
            created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        )
```

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/research/test_offline_dry_run.py::test_dry_run_rejects_real_source_until_real_research_path_exists -v`

Expected: fail until dry-run uses the identity contract.

- [ ] **Step 3: Implement identity-backed guard**

Replace `_require_fixture_dry_run_identity` with a call to `validate_source_identity`. Allow only `FIXTURE_ONLY` through the existing fixture dry-run path. If status is `BLOCKED`, raise with blocked reasons. If status is a future real-source status, raise `"real-source dry-run path is not implemented in Phase 16"`.

- [ ] **Step 4: Run dry-run tests**

Run: `python -m pytest tests/research/test_offline_dry_run.py -v`

Expected: pass.

---

### Task 4: Phase 16 Validator and Report

**Files:**
- Create: `tools/validate_phase16.py`
- Create: `docs/implementation-reports/phase-16-real-source-identity-contracts.md`
- Test: `tests/research/test_phase16_validator.py`

**Interfaces:**
- Consumes: all Phase 16 public artifacts.
- Produces: a single command that proves Phase 16 contracts and schemas are wired.

- [ ] **Step 1: Write failing validator smoke test**

```python
def test_phase16_validator_runs_successfully():
    completed = subprocess.run(
        [sys.executable, "tools/validate_phase16.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 16 artifacts validated" in completed.stdout
```

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/research/test_phase16_validator.py -v`

Expected: fail because the validator does not exist.

- [ ] **Step 3: Implement validator**

`tools/validate_phase16.py` must:
- validate `configs/data/source-identity-policy.yaml` against `schemas/source_identity_policy.schema.json`
- assert fixture metadata returns `FIXTURE_ONLY`
- assert fixture identity blocks production actions
- assert real metadata using fixture canonical symbol is blocked
- assert real metadata without `human_decision_ref` is blocked
- assert source bundle payload includes `source_identity`
- run `python tools/validate_phase15.py` as a regression gate
- print `Phase 16 artifacts validated`

- [ ] **Step 4: Write implementation report**

The report must include:
- scope
- files
- tests
- decisions
- unresolved risks
- next phase

- [ ] **Step 5: Run verification**

Run:
- `python -m pytest tests/data_foundation/test_source_identity.py -v`
- `python -m pytest tests/data_foundation/test_csv_onboarding.py tests/research/test_source_bundle.py tests/research/test_offline_dry_run.py -v`
- `python -m pytest tests/research/test_phase16_validator.py -v`
- `python tools/validate_phase15.py`
- `python tools/validate_phase16.py`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`

Expected: all commands pass.

---

## Self-Review

- Spec coverage: covers source identity, fixture separation, human-decision boundaries, OHLCV-only progress, and no production approval.
- Placeholder scan: no unresolved placeholder markers or undefined task references remain.
- Type consistency: all new symbols are defined in Task 1 before being consumed by Tasks 2-4.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-31-phase-16-real-source-identity-contracts.md`.

Recommended execution: Claude Code implements Tasks 1-4. Groq reviews the plan and the eventual implementation for bypasses, contradiction with Phase 15, fixture leakage, and hidden approval paths.

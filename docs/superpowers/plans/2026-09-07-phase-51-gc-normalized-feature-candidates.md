# Phase 51 GC Normalized Feature Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Phase 50 diagnostics into a research-only candidate feature set for the next GC model, excluding raw regime-drifted fields and defining normalized replacements.

**Architecture:** Phase 51 reads the sanitized Phase 50 feature diagnostics report and produces a sanitized feature-candidate report. It does not read raw market rows, does not train a model, and does not authorize promotion.

**Tech Stack:** Python, JSON schema, existing sanitized model/dataset diagnostics artifacts.

**Spec:** `configs/models/gc-feature-diagnostics-report.json`, `docs/implementation-reports/phase-50-gc-feature-diagnostics-and-experiment-design.md`

## Global Constraints

- Do not commit or push.
- Do not train a new model in Phase 51.
- Do not claim edge.
- Do not promote any model.
- Do not authorize live trading, broker execution, or capital allocation.
- Use only the sanitized Phase 50 feature diagnostics report.
- Use `order_flow` as the research variant.
- Do not write local absolute paths, secrets, API keys, or raw market rows.
- Exclude raw `close` and raw `atr_14` from the next model feature set because Phase 50 showed material TRAIN-to-TEST drift.

---

### Task 1: Normalized Feature Candidate Contract

**Files:**
- Create: `tests/models/test_gc_normalized_feature_candidates.py`
- Create: `trading_system/models/gc_normalized_feature_candidates.py`
- Create: `schemas/gc_normalized_feature_candidates_report.schema.json`

**Interfaces:**
- Consumes: `feature_diagnostics: dict`, `created_at: datetime`
- Produces: `build_gc_normalized_feature_candidates_report(...) -> GcNormalizedFeatureCandidatesReport`

- [ ] **Step 1: Write failing tests**

```python
def test_normalized_feature_candidates_exclude_raw_drifted_features_and_allow_research_training():
    report = build_gc_normalized_feature_candidates_report(feature_diagnostics(), created_at=FIXED_TIME).to_payload()
    assert report["status"] == "NORMALIZED_FEATURE_CANDIDATES_READY"
    assert report["research_training_allowed"] is True
    assert report["model_promotion_allowed"] is False
    assert "close" not in report["next_model_feature_set"]
    assert "atr_14" not in report["next_model_feature_set"]
    assert "atr_14_over_close" in report["next_model_feature_set"]
    assert "of_delta_over_of_volume" in report["next_model_feature_set"]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_normalized_feature_candidates.py -q`

Expected: FAIL because `trading_system.models.gc_normalized_feature_candidates` does not exist.

- [ ] **Step 3: Implement module and schema**

Implement:
- deterministic report id
- raw feature exclusions for `close` and `atr_14`
- normalized replacement feature definitions
- leakage guard fields that must never be used as model inputs
- research-only next-phase routing to `PHASE_52_NORMALIZED_FEATURE_MODEL_RETRAINING`

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_normalized_feature_candidates.py -q`

Expected: PASS.

### Task 2: CLI And Validator

**Files:**
- Create: `tools/gc_normalized_feature_candidates.py`
- Create: `tools/validate_phase51.py`
- Create: `tests/models/test_gc_normalized_feature_candidates_cli.py`
- Create: `tests/research/test_phase51_validator.py`
- Create: `configs/models/gc-normalized-feature-candidates-report.json`

**Interfaces:**
- Consumes: Phase 50 diagnostics report
- Produces: sanitized JSON report and validator output `Phase 51 artifacts validated`

- [ ] **Step 1: Write failing CLI and validator tests**

```python
def test_gc_normalized_feature_candidates_cli_writes_report(tmp_path):
    result = subprocess.run([...], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["research_training_allowed"] is True

def test_phase51_validator_accepts_normalized_feature_candidates_report():
    result = subprocess.run([sys.executable, "tools/validate_phase51.py"], check=True, capture_output=True, text=True)
    assert "Phase 51 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_normalized_feature_candidates_cli.py tests\research\test_phase51_validator.py -q`

Expected: FAIL because the CLI and validator do not exist.

- [ ] **Step 3: Implement CLI, validator, and real report generation**

The validator must run `tools/validate_phase50.py`, validate the Phase 51 schema, require research training allowed, require model promotion blocked, require raw `close` and `atr_14` excluded, require normalized replacements present, and verify no local paths are present in the sanitized report.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_normalized_feature_candidates_cli.py tests\research\test_phase51_validator.py -q`

Expected: PASS.

### Task 3: Human Report And Status

**Files:**
- Create: `docs/implementation-reports/phase-51-gc-normalized-feature-candidates.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-51-gc-normalized-feature-candidates-result.md`

**Interfaces:**
- Consumes: Phase 51 JSON candidate report
- Produces: concise explanation of the next trainable research feature set

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests\models\test_gc_normalized_feature_candidates.py tests\models\test_gc_normalized_feature_candidates_cli.py tests\research\test_phase51_validator.py -q
python tools\validate_phase51.py
```

- [ ] **Step 2: Write report and status**

Record excluded raw features, approved existing features, normalized candidate features, leakage guard, research-training permission, and blocked promotion boundary.

## Self-Review

- Spec coverage: The plan covers normalized candidates, exclusions, CLI, validator, report, and status.
- Placeholder scan: No banned placeholder markers remain.
- Type consistency: `build_gc_normalized_feature_candidates_report`, `GcNormalizedFeatureCandidatesReport`, and `gc-normalized-feature-candidates-report.json` are consistent.

# Phase 52 GC Normalized Feature Model Retraining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a research-only GC model using the Phase 51 normalized feature candidates and compare it against the previous real-model run without promoting it.

**Architecture:** Phase 52 loads validated Phase 46 candidate rows and the sanitized Phase 51 feature-candidate report. It materializes normalized feature values per row, trains an in-repo regularized logistic model with TRAIN-only fitting, selects threshold on VALIDATION only, evaluates on TEST only, and emits a sanitized run artifact.

**Tech Stack:** Python, numpy, pandas, pyarrow, JSON schema, existing training-readiness and GC dataset loaders.

**Spec:** `configs/models/gc-normalized-feature-candidates-report.json`, `configs/models/gc-first-real-model-run.json`, `configs/models/gc-majority-baseline-training-run.json`

## Global Constraints

- Do not commit or push.
- Research training is allowed only because Phase 51 set `research_training_allowed: true`.
- Do not claim edge.
- Do not promote any model.
- Do not authorize live trading, broker execution, or capital allocation.
- Preserve TRAIN-only imputation and standardization.
- Preserve VALIDATION-only threshold selection.
- Preserve TEST-only final evaluation.
- Do not allow `close`, `atr_14`, labels, outcome fields, or trade-contract prices as model inputs.
- Do not write local absolute paths, secrets, API keys, or raw market rows.

---

### Task 1: Normalized Feature Materialization And Training Contract

**Files:**
- Create: `tests/models/test_gc_normalized_feature_model.py`
- Create: `trading_system/models/gc_normalized_feature_model.py`
- Create: `schemas/gc_normalized_feature_model_run.schema.json`

**Interfaces:**
- Consumes: `rows: Sequence[CandidateTrainingRow]`, `policy: TrainingPolicy`, `feature_candidates: dict`, `previous_model_run: dict`, `baseline_run: dict`, `created_at: datetime`
- Produces: `train_gc_normalized_feature_model(...) -> GcNormalizedFeatureModelRun`
- Produces: `materialize_normalized_features(row, feature_candidates) -> dict[str, float | None]`

- [ ] **Step 1: Write failing tests**

```python
def test_normalized_feature_model_materializes_ratios_and_excludes_raw_drifted_inputs():
    payload = train_gc_normalized_feature_model(rows, policy, candidates, previous, baseline, created_at=FIXED_TIME).to_payload()
    assert payload["status"] == "TRAINED"
    assert "close" not in payload["feature_names"]
    assert "atr_14" not in payload["feature_names"]
    assert "atr_14_over_close" in payload["feature_names"]
    assert payload["promotion_allowed"] is False
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_normalized_feature_model.py -q`

Expected: FAIL because `trading_system.models.gc_normalized_feature_model` does not exist.

- [ ] **Step 3: Implement module and schema**

Implement:
- zero-safe normalized ratio materialization
- feature candidate gate
- forbidden-input guard
- logistic model training using only candidate feature names
- comparison metrics versus the Phase 48 model and majority baseline

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_normalized_feature_model.py -q`

Expected: PASS.

### Task 2: CLI, Real Run, And Validator

**Files:**
- Create: `tools/train_gc_normalized_feature_model.py`
- Create: `tools/validate_phase52.py`
- Create: `tests/models/test_train_gc_normalized_feature_model_cli.py`
- Create: `tests/research/test_phase52_validator.py`
- Create: `configs/models/gc-normalized-feature-model-run.json`

**Interfaces:**
- Consumes: Phase 46 build manifest, Phase 51 feature candidates, Phase 48 previous model run, majority baseline run, and baseline training policy
- Produces: sanitized JSON run and validator output `Phase 52 artifacts validated`

- [ ] **Step 1: Write failing CLI and validator tests**

```python
def test_train_gc_normalized_feature_model_cli_writes_sanitized_run(tmp_path):
    result = subprocess.run([...], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["model_type"] == "REGULARIZED_LOGISTIC_NORMALIZED_FEATURE_RESEARCH"

def test_phase52_validator_accepts_normalized_feature_model_run():
    result = subprocess.run([sys.executable, "tools/validate_phase52.py"], check=True, capture_output=True, text=True)
    assert "Phase 52 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_train_gc_normalized_feature_model_cli.py tests\research\test_phase52_validator.py -q`

Expected: FAIL because the CLI, validator, or run artifact does not exist.

- [ ] **Step 3: Implement CLI, validator, and real training run**

The validator must run `tools/validate_phase51.py`, validate schema, require promotion blocked, require raw drifted features excluded, require normalized features present, and verify sanitized output.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_train_gc_normalized_feature_model_cli.py tests\research\test_phase52_validator.py -q`

Expected: PASS.

### Task 3: Human Report And Status

**Files:**
- Create: `docs/implementation-reports/phase-52-gc-normalized-feature-model-retraining.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-52-gc-normalized-feature-model-retraining-result.md`

**Interfaces:**
- Consumes: Phase 52 run JSON
- Produces: concise explanation of metrics and next action

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests\models\test_gc_normalized_feature_model.py tests\models\test_train_gc_normalized_feature_model_cli.py tests\research\test_phase52_validator.py -q
python tools\validate_phase52.py
```

- [ ] **Step 2: Write report and status**

Record feature set, validation/test metrics, baseline comparisons, and blocked promotion boundary.

## Self-Review

- Spec coverage: The plan covers normalized feature materialization, model training, CLI, validator, real run, report, and status.
- Placeholder scan: No banned placeholder markers remain.
- Type consistency: `train_gc_normalized_feature_model`, `GcNormalizedFeatureModelRun`, and `gc-normalized-feature-model-run.json` are consistent.

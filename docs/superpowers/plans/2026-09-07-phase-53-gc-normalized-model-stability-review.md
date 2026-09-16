# Phase 53 GC Normalized Model Stability Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stress-test the Phase 52 normalized GC model across TEST months, direction regimes, volatility regimes, and nearby thresholds before any promotion discussion.

**Architecture:** Phase 53 reloads the validated Phase 46 rows, the Phase 51 feature candidates, and the Phase 52 model run. It reconstructs TRAIN-only imputation/standardization from the locked TRAIN rows, scores TEST rows using saved coefficients, and emits a sanitized stability report.

**Tech Stack:** Python, numpy, pandas, JSON schema, existing GC dataset loaders and normalized feature materialization.

**Spec:** `configs/models/gc-normalized-feature-model-run.json`, `configs/models/gc-normalized-feature-candidates-report.json`

## Global Constraints

- Do not claim edge.
- Do not promote any model.
- Do not authorize live trading, broker execution, or capital allocation.
- Do not retrain in Phase 53.
- Reconstruct preprocessing from TRAIN only.
- Evaluate stability on TEST only.
- Do not write local absolute paths, secrets, API keys, or raw market rows.

---

### Task 1: Stability Review Contract

**Files:**
- Create: `tests/models/test_gc_normalized_model_stability.py`
- Create: `trading_system/models/gc_normalized_model_stability.py`
- Create: `schemas/gc_normalized_model_stability_report.schema.json`

**Interfaces:**
- Consumes: `rows: Sequence[CandidateTrainingRow]`, `feature_candidates: dict`, `model_run: dict`, `created_at: datetime`
- Produces: `build_gc_normalized_model_stability_report(...) -> GcNormalizedModelStabilityReport`

- [ ] **Step 1: Write failing tests**

```python
def test_stability_report_scores_test_segments_and_keeps_promotion_blocked():
    report = build_gc_normalized_model_stability_report(rows, candidates, model_run, created_at=FIXED_TIME).to_payload()
    assert report["status"] == "STABILITY_REVIEW_REQUIRED"
    assert report["promotion_allowed"] is False
    assert report["evaluation_scope"] == "TEST_ONLY"
    assert report["preprocessing_reconstruction_scope"] == "TRAIN_ONLY"
    assert report["monthly_test_segments"]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_normalized_model_stability.py -q`

Expected: FAIL because `trading_system.models.gc_normalized_model_stability` does not exist.

- [ ] **Step 3: Implement module and schema**

Implement:
- TEST scoring using saved model coefficients
- month, direction, and volatility regime segments
- threshold perturbation checks
- blocked promotion boundary

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_normalized_model_stability.py -q`

Expected: PASS.

### Task 2: CLI, Report, And Validator

**Files:**
- Create: `tools/gc_normalized_model_stability.py`
- Create: `tools/validate_phase53.py`
- Create: `tests/models/test_gc_normalized_model_stability_cli.py`
- Create: `tests/research/test_phase53_validator.py`
- Create: `configs/models/gc-normalized-model-stability-report.json`

**Interfaces:**
- Consumes: Phase 46 rows, Phase 51 feature candidates, and Phase 52 model run
- Produces: sanitized JSON report and validator output `Phase 53 artifacts validated`

- [ ] **Step 1: Write failing CLI and validator tests**

```python
def test_gc_normalized_model_stability_cli_writes_report(tmp_path):
    result = subprocess.run([...], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["promotion_allowed"] is False

def test_phase53_validator_accepts_stability_report():
    result = subprocess.run([sys.executable, "tools/validate_phase53.py"], check=True, capture_output=True, text=True)
    assert "Phase 53 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_normalized_model_stability_cli.py tests\research\test_phase53_validator.py -q`

Expected: FAIL because CLI, validator, or report artifact does not exist.

- [ ] **Step 3: Implement CLI, validator, and real report generation**

The validator must run `tools/validate_phase52.py`, validate schema, require promotion blocked, require TEST-only evaluation, and verify sanitized output.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_normalized_model_stability_cli.py tests\research\test_phase53_validator.py -q`

Expected: PASS.

## Self-Review

- Spec coverage: The plan covers stability segmentation, threshold stress, CLI, validator, and report artifact.
- Placeholder scan: No banned placeholder markers remain.
- Type consistency: `build_gc_normalized_model_stability_report`, `GcNormalizedModelStabilityReport`, and `gc-normalized-model-stability-report.json` are consistent.

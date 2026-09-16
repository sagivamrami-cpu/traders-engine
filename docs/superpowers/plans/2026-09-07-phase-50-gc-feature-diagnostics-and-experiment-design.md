# Phase 50 GC Feature Diagnostics And Experiment Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-only diagnostics layer that identifies which GC tree-derived features and regimes need investigation after the Phase 48 model failed to confirm on TEST.

**Architecture:** Phase 50 reads the locked Phase 46 rows parquet, the Phase 48 first-model run, and the Phase 49 diagnostics report. It computes feature drift, simple target/return separation, and regime outcome summaries without fitting a new model or changing labels.

**Tech Stack:** Python, pandas, pyarrow, JSON schema, existing sanitized model/dataset manifests.

**Spec:** `docs/implementation-reports/phase-49-gc-model-diagnostics.md`, `configs/models/gc-model-diagnostics-report.json`, `configs/models/gc-first-real-model-run.json`, `configs/datasets/gc-30m-real-dataset-build-manifest.json`

## Global Constraints

- Do not commit or push.
- Do not train a new model in Phase 50.
- Do not claim edge.
- Do not promote any model.
- Do not authorize live trading, broker execution, or capital allocation.
- Use only the Phase 46 validated rows parquet and Phase 48/49 sanitized reports.
- Use `order_flow` as the diagnostics variant.
- Do not write local absolute paths, secrets, API keys, or raw market rows.

---

### Task 1: Feature Diagnostics Contract

**Files:**
- Create: `tests/models/test_gc_feature_diagnostics.py`
- Create: `trading_system/models/gc_feature_diagnostics.py`
- Create: `schemas/gc_feature_diagnostics_report.schema.json`

**Interfaces:**
- Consumes: `rows: pandas.DataFrame`, `build_manifest: dict`, `first_model_run: dict`, `model_diagnostics: dict`, `created_at: datetime`
- Produces: `build_gc_feature_diagnostics_report(...) -> GcFeatureDiagnosticsReport`

- [ ] **Step 1: Write failing tests**

```python
def test_feature_diagnostics_reports_drift_regimes_and_blocks_promotion():
    report = build_gc_feature_diagnostics_report(rows, manifest, first_model, diagnostics, created_at=FIXED_TIME).to_payload()
    assert report["status"] == "EXPERIMENT_DESIGN_REQUIRED"
    assert report["promotion_allowed"] is False
    assert report["diagnostic_focus"] == "FEATURE_AND_REGIME_STABILITY"
    assert report["top_drift_features"][0]["feature"] == "of_delta"
    assert "ORDER_FLOW_FEATURE_STABILITY_REVIEW" in report["recommended_experiments"]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_feature_diagnostics.py -q`

Expected: FAIL because `trading_system.models.gc_feature_diagnostics` does not exist.

- [ ] **Step 3: Implement module and schema**

Implement:
- feature drift: TRAIN mean/std vs VALIDATION/TEST mean
- target separation: TARGET_FIRST mean minus non-target mean on TRAIN
- regime summaries for direction, order-flow delta sign, momentum sign, and ATR terciles
- recommendation flags based on drift and negative Phase 49 result

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_feature_diagnostics.py -q`

Expected: PASS.

### Task 2: CLI And Validator

**Files:**
- Create: `tools/gc_feature_diagnostics.py`
- Create: `tools/validate_phase50.py`
- Create: `tests/models/test_gc_feature_diagnostics_cli.py`
- Create: `tests/research/test_phase50_validator.py`
- Create: `configs/models/gc-feature-diagnostics-report.json`

**Interfaces:**
- Consumes: Phase 46 build manifest, rows root, Phase 48 model run, Phase 49 diagnostics report
- Produces: sanitized JSON report and validator output `Phase 50 artifacts validated`

- [ ] **Step 1: Write failing CLI and validator tests**

```python
def test_gc_feature_diagnostics_cli_writes_report(tmp_path):
    result = subprocess.run([...], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["promotion_allowed"] is False

def test_phase50_validator_accepts_feature_diagnostics_report():
    result = subprocess.run([sys.executable, "tools/validate_phase50.py"], check=True, capture_output=True, text=True)
    assert "Phase 50 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_feature_diagnostics_cli.py tests\research\test_phase50_validator.py -q`

Expected: FAIL because the CLI and validator do not exist.

- [ ] **Step 3: Implement CLI, validator, and real report generation**

The validator must run `tools/validate_phase49.py`, validate the Phase 50 schema, require promotion blocked, require feature/regime diagnostics, and verify no local paths are present in the sanitized report.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_feature_diagnostics_cli.py tests\research\test_phase50_validator.py -q`

Expected: PASS.

### Task 3: Human Report And Status

**Files:**
- Create: `docs/implementation-reports/phase-50-gc-feature-diagnostics-and-experiment-design.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-50-gc-feature-diagnostics-result.md`

**Interfaces:**
- Consumes: Phase 50 JSON diagnostics report
- Produces: concise explanation of what to investigate next

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests\models\test_gc_feature_diagnostics.py tests\models\test_gc_feature_diagnostics_cli.py tests\research\test_phase50_validator.py -q
python tools\validate_phase50.py
```

- [ ] **Step 2: Write report and status**

Record the top unstable features, most useful regime summaries, recommended experiments, and the blocked promotion boundary.

## Self-Review

- Spec coverage: The plan covers feature diagnostics, regime summaries, CLI, validator, report, and status.
- Placeholder scan: No banned placeholder markers remain.
- Type consistency: `build_gc_feature_diagnostics_report`, `GcFeatureDiagnosticsReport`, and `gc-feature-diagnostics-report.json` are consistent.

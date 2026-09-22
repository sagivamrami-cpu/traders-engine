# Phase 49 GC Model Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a research-only diagnostics report that compares the Phase 48 first real GC model to the majority baseline and blocks promotion when TEST performance does not confirm the validation signal.

**Architecture:** Phase 49 is a manifest-only diagnostics layer. It reads the Phase 47 baseline run and Phase 48 first-real-model run, computes metric deltas, ranks model coefficients by absolute magnitude, records the review-fix status, and emits a sanitized JSON report plus validator.

**Tech Stack:** Python, JSON schema, existing `trading_system.data_foundation.manifests`, existing model run JSON artifacts.

**Spec:** `docs/implementation-reports/phase-48-first-real-gc-model.md`, `agent-exchange/reviews/2026-09-07T140500Z-codex-internal-review-phase-48-first-real-gc-model.md`

## Global Constraints

- Do not commit or push.
- Do not claim edge.
- Do not promote the model.
- Do not authorize live trading, broker execution, or capital allocation.
- Treat negative TEST expected R as promotion-blocking.
- Do not write local absolute paths, secrets, API keys, or raw market rows.

---

### Task 1: Diagnostics Contract

**Files:**
- Create: `tests/models/test_gc_model_diagnostics.py`
- Create: `trading_system/models/gc_model_diagnostics.py`
- Create: `schemas/gc_model_diagnostics_report.schema.json`

**Interfaces:**
- Consumes: `baseline_run: dict`, `first_model_run: dict`, `created_at: datetime`
- Produces: `build_gc_model_diagnostics_report(baseline_run, first_model_run, created_at) -> GcModelDiagnosticsReport`

- [ ] **Step 1: Write the failing test**

```python
def test_diagnostics_blocks_promotion_when_test_expected_r_is_negative():
    report = build_gc_model_diagnostics_report(BASELINE_RUN, FIRST_MODEL_RUN, created_at=FIXED_TIME).to_payload()
    assert report["status"] == "FEATURE_DIAGNOSTICS_REQUIRED"
    assert report["promotion_allowed"] is False
    assert "NEGATIVE_TEST_EXPECTED_R" in report["blocked_reasons"]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_model_diagnostics.py -q`

Expected: FAIL because `trading_system.models.gc_model_diagnostics` does not exist.

- [ ] **Step 3: Implement the minimal diagnostics module and schema**

Implement metric deltas, coefficient ranking, blocked reasons, and sanitized payload validation.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_model_diagnostics.py -q`

Expected: PASS.

### Task 2: CLI And Phase Validator

**Files:**
- Create: `tools/gc_model_diagnostics.py`
- Create: `tools/validate_phase49.py`
- Create: `tests/models/test_gc_model_diagnostics_cli.py`
- Create: `tests/research/test_phase49_validator.py`
- Create: `configs/models/gc-model-diagnostics-report.json`

**Interfaces:**
- Consumes: `configs/models/gc-majority-baseline-training-run.json`, `configs/models/gc-first-real-model-run.json`
- Produces: sanitized JSON report and validator output `Phase 49 artifacts validated`

- [ ] **Step 1: Write failing CLI and validator tests**

```python
def test_gc_model_diagnostics_cli_writes_report(tmp_path):
    result = subprocess.run([...], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["promotion_allowed"] is False

def test_phase49_validator_accepts_diagnostics_report():
    result = subprocess.run([sys.executable, "tools/validate_phase49.py"], check=True, capture_output=True, text=True)
    assert "Phase 49 artifacts validated" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_gc_model_diagnostics_cli.py tests\research\test_phase49_validator.py -q`

Expected: FAIL because the CLI and validator do not exist.

- [ ] **Step 3: Implement CLI, validator, and real report generation**

The validator must run `tools/validate_phase48.py`, validate the diagnostics schema, assert `promotion_allowed: false`, and require `NEGATIVE_TEST_EXPECTED_R` when TEST expected R is below zero.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_gc_model_diagnostics_cli.py tests\research\test_phase49_validator.py -q`

Expected: PASS.

### Task 3: Report And Status

**Files:**
- Create: `docs/implementation-reports/phase-49-gc-model-diagnostics.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-49-gc-model-diagnostics-result.md`

**Interfaces:**
- Consumes: Phase 49 validator output
- Produces: human-readable summary and shared status

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests\models\test_gc_model_diagnostics.py tests\models\test_gc_model_diagnostics_cli.py tests\research\test_phase49_validator.py -q
python tools\validate_phase49.py
```

- [ ] **Step 2: Write implementation report and shared status**

Record metric deltas, blocked reasons, feature ranking, and the recommendation for the next research phase.

## Self-Review

- Spec coverage: The plan covers diagnostics, CLI, validator, report, and status.
- Placeholder scan: No banned placeholder markers remain.
- Type consistency: `build_gc_model_diagnostics_report`, `GcModelDiagnosticsReport`, and `gc-model-diagnostics-report.json` are consistent.

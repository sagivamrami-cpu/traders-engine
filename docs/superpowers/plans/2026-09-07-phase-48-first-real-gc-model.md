# Phase 48 First Real GC Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train and evaluate the first real predictive GC 30m research model against the Phase 47 majority-class baseline.

**Architecture:** Keep Phase 48 as a research-only model layer on top of the locked Phase 46 dataset. The model consumes `CandidateTrainingRow` records from the validated build manifest, trains only on the chronological TRAIN split, selects thresholds on VALIDATION, and reports final performance on TEST without promotion authority.

**Tech Stack:** Python, pandas, pyarrow, existing `trading_system.models` contracts, existing GC dataset manifest/readiness loaders.

**Spec:** `docs/superpowers/plans/2026-09-02-phases-43-47-gc-real-dataset-to-training-start.md`, `docs/implementation-reports/phase-46-47-gc-real-dataset-build-and-training-start.md`, `configs/datasets/gc-30m-real-dataset-build-manifest.json`, `configs/models/baseline-training-policy.yaml`

## Global Constraints

- Do not commit or push unless the human explicitly changes the current instruction.
- Use only the validated Phase 46 dataset manifest for the first real model.
- Use `order_flow` as the first real model variant.
- Do not use random time-series splits.
- Fit all transforms only inside TRAIN.
- Select model threshold and hyperparameters only on VALIDATION.
- Use TEST only once for final report.
- Exclude ambiguous labels from model training.
- Keep HHLL out of the primary training target.
- Keep model promotion blocked.
- Keep live trading, broker execution, and capital allocation blocked.
- Do not write local absolute paths, API keys, raw market rows, or vendor secrets into manifests, docs, or `agent-exchange/`.

---

## File Structure

- Create `trading_system/models/first_real_gc_model.py`: research model training and evaluation functions.
- Create `tools/train_gc_first_real_model.py`: CLI wrapper that loads the Phase 46 manifest, trains the model, and writes a sanitized run manifest.
- Create `schemas/gc_first_real_model_run.schema.json`: JSON schema for the Phase 48 run manifest.
- Create `tests/models/test_first_real_gc_model.py`: unit tests for train/validation/test behavior, no-leakage checks, and metric output.
- Create `tests/models/test_train_gc_first_real_model_cli.py`: CLI test with a tiny parquet fixture.
- Create `tools/validate_phase48.py`: phase validator that requires Phase 47, validates the run manifest, and confirms promotion remains blocked.
- Create `tests/research/test_phase48_validator.py`: validator smoke test.
- Create `configs/models/gc-first-real-model-run.json`: sanitized run manifest written by the CLI.
- Create `docs/implementation-reports/phase-48-first-real-gc-model.md`: concise phase report after verification.

### Task 1: Model Contract And Tests

**Files:**
- Create: `tests/models/test_first_real_gc_model.py`
- Create: `trading_system/models/first_real_gc_model.py`
- Create: `schemas/gc_first_real_model_run.schema.json`

**Interfaces:**
- Consumes: `list[CandidateTrainingRow]`, `TrainingPolicy`
- Produces: `train_first_real_gc_model(rows, policy, created_at) -> FirstRealGcModelRun`

- [ ] **Step 1: Write the failing tests**

```python
def test_first_real_model_fits_only_train_and_reports_validation_and_test_metrics():
    rows = fixture_candidate_rows()
    run = train_first_real_gc_model(rows, permissive_training_policy(), created_at=FIXED_TIME)
    payload = run.to_payload()
    assert payload["status"] == "TRAINED"
    assert payload["model_type"] == "REGULARIZED_LOGISTIC_RESEARCH_BASELINE"
    assert payload["promotion_allowed"] is False
    assert payload["fit_scope"] == "TRAIN_ONLY"
    assert payload["selection_scope"] == "VALIDATION_ONLY"
    assert payload["final_evaluation_scope"] == "TEST_ONLY"
    assert set(payload["metrics"]) >= {
        "validation_accuracy",
        "test_accuracy",
        "validation_balanced_accuracy",
        "test_balanced_accuracy",
    }
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_first_real_gc_model.py -q`

Expected: FAIL because `trading_system.models.first_real_gc_model` does not exist.

- [ ] **Step 3: Implement the minimal model module**

Implement:

```python
@dataclass(frozen=True)
class FirstRealGcModelRun:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def train_first_real_gc_model(
    rows: Sequence[CandidateTrainingRow],
    policy: TrainingPolicy,
    *,
    created_at: datetime,
) -> FirstRealGcModelRun:
    ...
```

The first implementation may use a deterministic regularized linear classifier
from available local dependencies. If no classifier dependency is available,
implement a small in-repo binary logistic regression over numeric features with
fixed learning rate, fixed seed-free initialization, TRAIN-only standardization,
and one-vs-rest probabilities for `TARGET_FIRST` versus non-target outcomes.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_first_real_gc_model.py -q`

Expected: PASS.

### Task 2: CLI Training Entry Point

**Files:**
- Create: `tools/train_gc_first_real_model.py`
- Create: `tests/models/test_train_gc_first_real_model_cli.py`

**Interfaces:**
- Consumes: `candidate_rows_from_build_manifest(build_manifest_path, rows_root, variant)`
- Produces: sanitized JSON at `--run-out`

- [ ] **Step 1: Write the failing CLI test**

```python
def test_train_gc_first_real_model_cli_writes_sanitized_run(tmp_path):
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    run_out = tmp_path / "run.json"
    result = subprocess.run(
        [
            sys.executable,
            "tools/train_gc_first_real_model.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
            "--training-policy",
            "configs/models/baseline-training-policy.yaml",
            "--variant",
            "order_flow",
            "--run-out",
            str(run_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "TRAINED"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(run_out.read_text(encoding="utf-8")) == payload
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\models\test_train_gc_first_real_model_cli.py -q`

Expected: FAIL because the CLI does not exist.

- [ ] **Step 3: Implement CLI**

The CLI should mirror `tools/train_gc_majority_baseline.py`, but call
`train_first_real_gc_model`.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\models\test_train_gc_first_real_model_cli.py -q`

Expected: PASS.

### Task 3: Train On The Real GC Dataset

**Files:**
- Create: `configs/models/gc-first-real-model-run.json`

**Interfaces:**
- Consumes: `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- Produces: `configs/models/gc-first-real-model-run.json`

- [ ] **Step 1: Run Phase 47 gate**

Run: `python tools\validate_phase47.py`

Expected: PASS with `Phase 47 artifacts validated`.

- [ ] **Step 2: Train the first real model**

Run:

```powershell
python tools\train_gc_first_real_model.py --build-manifest configs\datasets\gc-30m-real-dataset-build-manifest.json --rows-root market-data\gc-30m-real --training-policy configs\models\baseline-training-policy.yaml --variant order_flow --run-out configs\models\gc-first-real-model-run.json
```

Expected: PASS and writes a sanitized JSON run manifest.

- [ ] **Step 3: Inspect the run**

Confirm:
- `status` is `TRAINED`
- `model_type` is not `MAJORITY_CLASS_BASELINE`
- `promotion_allowed` is `false`
- validation and test metrics are present
- output contains no local absolute paths

### Task 4: Phase 48 Validator

**Files:**
- Create: `tests/research/test_phase48_validator.py`
- Create: `tools/validate_phase48.py`

**Interfaces:**
- Consumes: `configs/models/gc-first-real-model-run.json`
- Produces: validator output `Phase 48 artifacts validated`

- [ ] **Step 1: Write the failing validator test**

```python
def test_phase48_validator_accepts_first_real_gc_model_run():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase48.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Phase 48 artifacts validated" in result.stdout
    assert result.stderr == ""
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests\research\test_phase48_validator.py -q`

Expected: FAIL because `tools/validate_phase48.py` does not exist.

- [ ] **Step 3: Implement validator**

The validator must:
- run `tools/validate_phase47.py`
- validate `gc-first-real-model-run.json` against `gc_first_real_model_run.schema.json`
- assert the dataset id matches the Phase 46 manifest
- assert model type differs from `MAJORITY_CLASS_BASELINE`
- assert TRAIN, VALIDATION, and TEST counts match the Phase 47 `order_flow` rows
- assert `promotion_allowed` is `false`
- assert no local absolute path is present

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests\research\test_phase48_validator.py -q`

Expected: PASS.

### Task 5: Report And Review

**Files:**
- Create: `docs/implementation-reports/phase-48-first-real-gc-model.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-48-first-real-gc-model-result.md`
- Optionally create: `agent-exchange/inbox/claude-code/YYYY-MM-DDTHHMMSSZ-claude-code-review-phase-48-first-real-gc-model.md`

**Interfaces:**
- Consumes: Phase 48 run manifest and validator output
- Produces: human-readable result and optional Claude Code review request

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests\models\test_first_real_gc_model.py tests\models\test_train_gc_first_real_model_cli.py tests\research\test_phase48_validator.py -q
python tools\validate_phase48.py
```

Expected: PASS.

- [ ] **Step 2: Write implementation report**

Record:
- feature set used
- model family
- validation metrics
- test metrics
- comparison to majority baseline
- blocked promotion/live actions

- [ ] **Step 3: Write shared status**

Use `agent-exchange/templates/result.md` structure and include exact
verification commands.

- [ ] **Step 4: Request review if useful**

If the first real model beats the baseline or has surprising metrics, ask Claude
Code to review leakage risk, split handling, and metric interpretation before
using the result to plan any next phase.

## Self-Review

- Spec coverage: The plan covers model contract, training CLI, real dataset
  execution, phase validation, reporting, and review routing.
- Placeholder scan: No banned placeholder markers or undefined future work terms remain.
- Type consistency: `train_first_real_gc_model`, `FirstRealGcModelRun`, and
  `gc-first-real-model-run.json` are named consistently across tasks.

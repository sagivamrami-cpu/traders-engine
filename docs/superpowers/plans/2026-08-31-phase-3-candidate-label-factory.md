# Phase 3 Candidate and Label Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fixture-only CandidateAction, TradeContract, and OutcomeLabel factory over Phase 2 UnifiedMarketState snapshots.

**Architecture:** Add `trading_system/candidates` modules that consume Phase 2 snapshots and Phase 1 normalized bars. Candidate generation is deterministic, logs eligible and rejected candidates, and creates labels only from future bars according to a versioned trade contract.

**Tech Stack:** Python 3.9+, pytest, PyYAML, jsonschema, dataclasses, hashlib, datetime.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture, task routing, and acceptance decisions for implementation quality.
- No model training starts in Phase 3.
- No backtesting engine, broker calls, live trading, or capital allocation logic is allowed.
- Every CandidateAction must validate against `schemas/candidate_action.schema.json`.
- Every TradeContract must validate against `schemas/trade_contract.schema.json`.
- Every OutcomeLabel must validate against `schemas/outcome_label.schema.json`.
- Candidate generation and candidate rejection are both logged.
- A label may use only bars after the candidate observation time.
- If target and stop are both touched in the same bar without tick path, the label is `AMBIGUOUS` and `EXCLUDED_FROM_TRAINING`.
- Touching a price is not proof of fill; fixture contracts use a deterministic close-entry assumption only for offline label construction.

---

## File Structure

Create or modify these files only:

- `configs/candidates/fixture-graph-rules.yaml`: fixture-only candidate and contract parameters.
- `trading_system/candidates/__init__.py`: candidate package exports.
- `trading_system/candidates/contracts.py`: CandidateAction, TradeContract, OutcomeLabel dataclasses.
- `trading_system/candidates/generation.py`: fixture candidate generator and deterministic ids.
- `trading_system/candidates/labeling.py`: fixture outcome labeler.
- `tools/validate_phase3.py`: validates candidate, contract, label, and replay stability.
- `tests/candidates/test_candidate_contracts.py`: schema-compatible payload tests.
- `tests/candidates/test_candidate_generation.py`: eligible/rejected candidate tests.
- `tests/candidates/test_labeling.py`: target/stop/expired/ambiguous label tests.
- `tests/candidates/test_phase3_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-3-candidate-label-factory.md`: Phase 3 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Telegram delivery code
- Notion delivery code
- model, training, backtest, broker, or live execution modules

---

## Implementation Tasks

### Task 1: Candidate and Label Contracts

**Files:**
- Create: `trading_system/candidates/__init__.py`
- Create: `trading_system/candidates/contracts.py`
- Create: `tests/candidates/test_candidate_contracts.py`

**Interfaces:**
- Consumes: Phase 0 candidate, trade contract, and outcome label schemas.
- Produces: `CandidateAction.to_payload()`, `TradeContract.to_payload()`, `OutcomeLabel.to_payload()`.

- [ ] **Step 1: Write failing contract tests**

Validate one payload for each dataclass against the matching schema.

- [ ] **Step 2: Run contract tests**

Run: `python -m pytest tests/candidates/test_candidate_contracts.py -v`

Expected: fail because `trading_system.candidates` does not exist.

- [ ] **Step 3: Implement contract dataclasses**

Use UTC `Z` datetime serialization and no extra payload keys.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/candidates/test_candidate_contracts.py -v`

Expected: pass.

---

### Task 2: Fixture Candidate Generation

**Files:**
- Create: `configs/candidates/fixture-graph-rules.yaml`
- Create: `trading_system/candidates/generation.py`
- Create: `tests/candidates/test_candidate_generation.py`

**Interfaces:**
- Consumes: `UnifiedMarketState`.
- Produces: `generate_fixture_candidate(snapshot, created_at) -> CandidateAction`.

- [ ] **Step 1: Write candidate tests**

Tests must verify:

- a valid snapshot with positive `price.return_pct` emits `ELIGIBLE` LONG.
- a degraded snapshot emits `REJECTED` LONG.
- candidate id is deterministic for the same snapshot and graph rule.
- rejected candidates keep reasons.
- payload validates against `candidate_action.schema.json`.

- [ ] **Step 2: Run candidate tests**

Run: `python -m pytest tests/candidates/test_candidate_generation.py -v`

Expected: fail because candidate generator does not exist.

- [ ] **Step 3: Implement generator**

Use graph id `tr-vshape-retest-long`, graph version `fixture-graph-rules-0.1.0`, producer `TR`, direction `LONG`, expiry one minute after creation, and reason codes from deterministic data-quality checks.

- [ ] **Step 4: Run candidate tests**

Run: `python -m pytest tests/candidates/test_candidate_generation.py -v`

Expected: pass.

---

### Task 3: Fixture Trade Contract and Labeling

**Files:**
- Create: `trading_system/candidates/labeling.py`
- Create: `tests/candidates/test_labeling.py`

**Interfaces:**
- Consumes: `CandidateAction`, candidate bar, future bars.
- Produces: `build_fixture_trade_contract(candidate_bar) -> TradeContract`, `label_long_candidate(candidate, contract, future_bars) -> OutcomeLabel`.

- [ ] **Step 1: Write label tests**

Tests must verify:

- target touched before stop emits `TARGET_FIRST`.
- stop touched before target emits `STOP_FIRST`.
- no target/stop touch before max bars emits `EXPIRED`.
- same bar target and stop emits `AMBIGUOUS` and `EXCLUDED_FROM_TRAINING`.
- rejected candidate emits `EXPIRED` with `filled=false` and `EXCLUDED_FROM_TRAINING`.
- label payload validates against `outcome_label.schema.json`.

- [ ] **Step 2: Run label tests**

Run: `python -m pytest tests/candidates/test_labeling.py -v`

Expected: fail because labeler does not exist.

- [ ] **Step 3: Implement fixture contract builder**

Use close entry, stop at candidate-bar low, target at 2R above entry, `max_holding_bars=2`, zero commission, fixture fill/slippage policy ids.

- [ ] **Step 4: Implement labeler**

Iterate future bars in observation order. For each bar:

- if both stop and target touch in the same bar, return `AMBIGUOUS`.
- if target touches first, return `TARGET_FIRST`.
- if stop touches first, return `STOP_FIRST`.
- after `max_holding_bars`, return `EXPIRED`.

- [ ] **Step 5: Run label tests**

Run: `python -m pytest tests/candidates/test_labeling.py -v`

Expected: pass.

---

### Task 4: Validator and Report

**Files:**
- Create: `tools/validate_phase3.py`
- Create: `tests/candidates/test_phase3_validator.py`
- Create: `docs/implementation-reports/phase-3-candidate-label-factory.md`

**Interfaces:**
- Consumes: Phase 1 fixture records and Phase 2 UMS snapshots.
- Produces: deterministic `python tools/validate_phase3.py` command.

- [ ] **Step 1: Write validator smoke test**

Test must call `python tools/validate_phase3.py` and assert exit code 0 and output `Phase 3 artifacts validated`.

- [ ] **Step 2: Run validator test**

Run: `python -m pytest tests/candidates/test_phase3_validator.py -v`

Expected: fail because validator does not exist.

- [ ] **Step 3: Implement validator**

Validator must build one eligible candidate, one rejected candidate, one trade contract, and one outcome label, then validate all payloads against Phase 0 schemas.

- [ ] **Step 4: Add implementation report**

Report must list scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 5: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates -v
python tools/validate_phase0.py
python tools/validate_phase1.py
python tools/validate_phase2.py
python tools/validate_phase3.py
```

Expected: all tests pass and all validators print validated messages.

---

## Acceptance Criteria

- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates -v` passes.
- `python tools/validate_phase0.py` passes.
- `python tools/validate_phase1.py` passes.
- `python tools/validate_phase2.py` passes.
- `python tools/validate_phase3.py` passes.
- Eligible and rejected candidates are both represented.
- Ambiguous labels are excluded from training.
- Rejected candidates do not receive filled trade labels.
- No model training, prediction, backtesting, broker integration, or live execution code is added.

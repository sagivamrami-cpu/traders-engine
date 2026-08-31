# Phase 14 Real-Data Decision Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let readiness reporting optionally merge a human-maintained decision file so satisfied checklist items appear in the report, without approving production data by default.

**Architecture:** Extend `trading_system/research/readiness.py` with a decision-file loader, a decision applier, and an optional `decisions` input on the report builder. A decision may satisfy only a known checklist `item_id`, and only when it is `APPROVED` and carries approver, timestamp, scope, and non-fixture evidence. The default repository state stays `BLOCKED` because no approving decision file is committed.

**Tech Stack:** Python 3.9+, pytest, jsonschema, PyYAML, argparse.

**Spec:** `agent-exchange/inbox/claude-code/2026-08-31T090000Z-claude-code-phase-14-decision-intake.md`

## Global Constraints

- A decision file may satisfy only known checklist `item_id` values.
- Each satisfied item must include approver, timestamp, decision, scope, and evidence.
- Unknown item ids must fail validation with `ValueError`.
- Missing approval or evidence fields must fail validation (loader `ValueError` and JSON-schema failure).
- The default repository state must remain `BLOCKED`; `satisfied_count` stays `0` with no decisions file and with the committed template.
- Fixture and synthetic data must not satisfy real-data readiness: `APPROVED` evidence or scope referencing `tests/fixtures`, `fixture`, or `synthetic` is rejected.
- The Phase 12 checklist file is not mutated to mark items satisfied.
- No vendor fetch, raw market data, secrets, broker or account data, production model training, backtesting, live trading, or capital allocation.
- No commits or pushes; changes stay uncommitted for Codex review.

---

## File Structure

Create:

- `schemas/real_data_decisions.schema.json`: decision-file contract.
- `configs/research/real-data-decisions-template.yaml`: explicitly non-approving template showing every required field.
- `tools/validate_phase14.py`: deterministic Phase 14 validator.
- `tests/research/test_phase14_validator.py`: validator smoke test.
- `docs/implementation-reports/phase-14-real-data-decision-intake.md`: Phase 14 report.

Modify:

- `trading_system/research/readiness.py`: decision dataclasses, loader, applier, report builder decisions support.
- `schemas/real_data_readiness_report.schema.json`: report version bump plus `decisions_version` and optional per-item `decision`.
- `tools/real_data_readiness.py`: optional `--decisions` argument.
- `tests/research/test_real_data_readiness.py`: decision intake tests.

Do not modify:

- `configs/research/real-data-readiness-checklist.yaml` item statuses.
- `engine/`, delivery code, broker, live execution, deployment, or promotion modules.

---

## Contracts

Decision file (YAML, validated by `schemas/real_data_decisions.schema.json`):

```yaml
version: real-data-decisions-0.1.0
decisions:
  - item_id: <known checklist item_id>
    decision: APPROVED | NOT_APPROVED
    approver: <human approver name>
    decided_at: <ISO 8601 timestamp with explicit offset>
    scope: <what exactly the decision covers>
    evidence:
      - <link or path to the decision record, e.g. agent-exchange/decisions/...>
```

Semantics:

- `APPROVED` marks the matching checklist item `SATISFIED` in the report and attaches the decision payload to the item.
- `NOT_APPROVED` records the decision on the item but leaves it `OPEN_HUMAN_DECISION`.
- An explicit defer or local-only resolution (per the checklist labels) is recorded as `APPROVED` with the defer scope spelled out; Codex may split this into a dedicated enum value at acceptance if preferred.
- Report payload gains required `decisions_version` (`string | null`), and `report_version` bumps to `real-data-readiness-report-0.2.0`.

New public interfaces in `trading_system/research/readiness.py`:

- `DECISIONS_VERSION = "real-data-decisions-0.1.0"`
- `RealDataDecision(item_id, decision, approver, decided_at, scope, evidence: tuple[str, ...])` with `to_payload()`
- `RealDataDecisionFile(version, decisions: tuple[RealDataDecision, ...])`
- `load_real_data_decisions(path: Path) -> RealDataDecisionFile` (raises `ValueError` on any structural problem)
- `apply_real_data_decisions(checklist, decision_file) -> RealDataReadinessChecklist` (raises `ValueError` on unknown or duplicate ids and fixture/synthetic evidence)
- `build_real_data_readiness_report(checklist, *, created_at, decisions=None)` (existing callers unchanged)

---

## Implementation Tasks

### Task 1: Decision schema, template, loader, and report merge

**Files:**
- Create: `schemas/real_data_decisions.schema.json`
- Create: `configs/research/real-data-decisions-template.yaml`
- Modify: `trading_system/research/readiness.py`
- Modify: `schemas/real_data_readiness_report.schema.json`
- Modify: `tests/research/test_real_data_readiness.py`

**Interfaces:**
- Consumes: existing `RealDataReadinessChecklist`, `build_real_data_readiness_report`, `utc_iso`.
- Produces: the loader/applier/builder signatures listed in Contracts.

- [ ] **Step 1: Write failing tests** in `tests/research/test_real_data_readiness.py` covering: template validates against decisions schema; template satisfies nothing (report stays `BLOCKED`, `satisfied_count == 0`); an `APPROVED` decision with all fields satisfies its known item and the merged report validates against the report schema; approving every item yields `READY_FOR_PRODUCTION_DATASET`; unknown `item_id` raises `ValueError`; duplicate `item_id` raises `ValueError`; missing `approver` fails both loader and schema; missing/empty `evidence` fails both; `NOT_APPROVED` does not satisfy; fixture/synthetic evidence raises `ValueError`; the default report exposes `decisions_version: null`.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/research/test_real_data_readiness.py -v`
Expected: new tests fail (`ImportError`/`FileNotFoundError`), pre-existing tests pass.

- [ ] **Step 3: Implement** the decisions schema, non-approving template (single `NOT_APPROVED` example entry with placeholder approver), readiness dataclasses/loader/applier, report-builder `decisions` keyword, `REPORT_VERSION` bump, and report-schema update.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/research/test_real_data_readiness.py -v`
Expected: pass.

---

### Task 2: CLI flag, Phase 14 validator, and reports

**Files:**
- Modify: `tools/real_data_readiness.py`
- Create: `tools/validate_phase14.py`
- Create: `tests/research/test_phase14_validator.py`
- Create: `docs/implementation-reports/phase-14-real-data-decision-intake.md`

**Interfaces:**
- Produces: `python tools/real_data_readiness.py [--decisions <path>]` and `python tools/validate_phase14.py` printing `Phase 14 artifacts validated`.

- [ ] **Step 1: Write validator smoke test** asserting `python tools/validate_phase14.py` exits 0 and prints `Phase 14 artifacts validated`.

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/research/test_phase14_validator.py -v`
Expected: fail because the validator does not exist.

- [ ] **Step 3: Implement** the `--decisions` argparse option (no-arg behavior unchanged) and `tools/validate_phase14.py`, which must: check the decisions schema and template; build default and template-merged reports and require `BLOCKED` with `satisfied_count == 0`; require `ValueError` for unknown ids and fixture evidence; require schema failure for missing approver/evidence; run the CLI with and without `--decisions` and validate both outputs against the report schema.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/research/test_phase14_validator.py -v`
Expected: pass.

- [ ] **Step 5: Write the implementation report** listing scope, files, tests, decisions, unresolved risks, and next phase.

- [ ] **Step 6: Full verification**

```bash
python -m pytest tests/research/test_real_data_readiness.py -v
python -m pytest tests/research/test_phase14_validator.py -v
python tools/validate_phase12.py
python tools/validate_phase13.py
python tools/validate_phase14.py
python tools/real_data_readiness.py
python tools/real_data_readiness.py --decisions configs/research/real-data-decisions-template.yaml
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v
```

Expected: everything passes; both CLI runs emit schema-valid `BLOCKED` reports.

---

## Acceptance Criteria

- Default readiness report and template-merged report are both `BLOCKED` with `satisfied_count == 0`.
- A human-authored decision file with full approval evidence can satisfy known items only.
- Unknown item ids, duplicates, missing approval/evidence fields, and fixture/synthetic evidence all fail.
- The Phase 12 checklist file is unchanged.
- All verification commands from the inbox request pass.
- No commits are made; work is left for Codex review.

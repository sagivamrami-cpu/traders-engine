# Phase 57: Tree Gate Baseline and Candidate Audit

## Purpose

Phase 57 creates a conservative rule-only baseline for the TR tree and audits every GC candidate against the 14 runtime stages.

This phase does not train a model. It shows what the current system can and cannot decide using explicit gates.

## Method

Each candidate is evaluated through the 14 TR runtime stages:

1. `DATA`
2. `POSITION`
3. `SESSION`
4. `LOCATION`
5. `CYCLE`
6. `CONTEXT`
7. `PATTERN`
8. `VECTOR`
9. `TRAP`
10. `RETEST`
11. `TARGET_RISK`
12. `TRIGGER`
13. `SCALE_IN`
14. `INVALIDATION`

The current baseline is intentionally conservative:

- implemented from existing rows: `DATA`, `SESSION`, `CONTEXT`, `TARGET_RISK`
- missing typed tree gates: `POSITION`, `LOCATION`, `CYCLE`, `PATTERN`, `VECTOR`, `TRAP`, `RETEST`, `TRIGGER`, `SCALE_IN`, `INVALIDATION`
- missing gates return `UNKNOWN`
- any candidate with missing mandatory tree stages returns `WAIT`
- candidates blocked at `DATA` return `NO_TRADE`
- the baseline never emits `LONG` or `SHORT` yet

## Audit Result

Rows evaluated: `380362`

Final actions:

- `WAIT`: `341056`
- `NO_TRADE`: `39306`
- `LONG`: `0`
- `SHORT`: `0`

Stage highlights:

- `DATA`
  - `PASS`: `341056`
  - `BLOCK`: `39306`
- `VECTOR`
  - `UNKNOWN`: `341056`
  - `NOT_EVALUATED`: `39306`
- `TRIGGER`
  - `UNKNOWN`: `341056`
  - `NOT_EVALUATED`: `39306`

## Trading Interpretation

This explains the gap between manual trading and the trained model.

The current pipeline has many rows that are eligible as data, but the actual trader decision path is still missing as typed gates. A human trader may reject or wait based on vector, trap, retest, trigger, location, and invalidation logic. The current model did not receive those gates as deterministic structure.

Therefore, the correct next move is not another flat model. The correct next move is typed tree gate implementation.

## Required Next Artifacts

- `typed_gate_schema_per_stage`
- `manual_tree_rule_parameters`
- `candidate_rejection_reason_catalog`
- `stage_level_replay_annotation`
- `long_short_gate_policy`
- `regime_gate_policy`

## Promotion Boundary

Still blocked:

- `TRAIN_ADDITIONAL_FLAT_MODEL`
- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_tree_gate_baseline_audit.schema.json`
- Module: `trading_system/models/gc_tree_gate_baseline.py`
- CLI: `tools/gc_tree_gate_baseline_audit.py`
- Validator: `tools/validate_phase57.py`
- Audit: `configs/models/gc-tree-gate-baseline-audit.json`
- Tests:
  - `tests/models/test_gc_tree_gate_baseline.py`
  - `tests/models/test_gc_tree_gate_baseline_cli.py`
  - `tests/research/test_phase57_validator.py`

## Verification

```powershell
python -m pytest tests\models\test_gc_tree_gate_baseline.py tests\models\test_gc_tree_gate_baseline_cli.py tests\research\test_phase57_validator.py -q
python tools\validate_phase57.py
python -m py_compile trading_system\models\gc_tree_gate_baseline.py tools\gc_tree_gate_baseline_audit.py tools\validate_phase57.py
```

Result:

- 4 tests passed.
- Phase 57 validator passed.
- Python compile check passed.
- Local path / secret scan found no matches.

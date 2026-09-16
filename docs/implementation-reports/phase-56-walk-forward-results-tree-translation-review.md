# Phase 56: Walk-Forward Results and Tree Translation Review

## Purpose

Phase 56 reviews the Phase 55 walk-forward result against the original tree-to-trained-model architecture.

This phase answers the practical question: why can a tree work in manual trading, while the current trained model does not show stable evidence?

## Main Finding

The current model is not yet the tree.

It is a flat logistic model over normalized features. The architecture requires a deterministic tree path first, with typed gates, pass/block reasons, candidate rejection logging, and then model scoring only inside valid candidate contexts.

## Walk-Forward Evidence

From Phase 55:

- Best primary experiment: `MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`
- Best primary median TEST expected R per candidate: `0.001314060446780552`
- Comparator median TEST expected R per candidate: `-0.001335841853257661`
- Comparator valid windows: `8`
- Comparator positive windows: `3`

Filtered experiments without valid windows:

- `LONG_MID_HIGH_VOLATILITY_WALK_FORWARD_RETRAINING`
- `LONG_ONLY_WALK_FORWARD_RETRAINING`
- `SHORT_ONLY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`
- `LOW_VOLATILITY_DIAGNOSTIC_WALK_FORWARD_RETRAINING`

Interpretation:

The all-candidate model family is weak in walk-forward evaluation. Filtered variants are underpowered under the current row thresholds. This does not prove the manual tree is invalid; it shows that the current machine translation is too coarse.

## Gap Codes

- `FLAT_MODEL_INSTEAD_OF_TREE_GATE_POLICY`
- `CANDIDATE_SELECTION_TOO_BROAD`
- `LABEL_TOO_NARROW_FOR_MANUAL_TRADING_PROCESS`
- `TREE_STAGE_COVERAGE_INCOMPLETE`
- `DIRECTION_AND_REGIME_LOGIC_NOT_SEPARATED`
- `MANUAL_SKIP_DECISIONS_NOT_CAPTURED`
- `RULE_ONLY_TREE_BASELINE_MISSING`

## Missing Manual Process Elements

The current pipeline does not yet capture:

- trader skip decisions,
- hierarchical gate path,
- setup quality annotation,
- direction-specific policy,
- regime-first filtering.

These are exactly the places where a manual trader can outperform a naive mechanical translation.

## Tree Stage Coverage

The 14 TR runtime stages are now represented in the review:

- `DATA`
- `POSITION`
- `SESSION`
- `LOCATION`
- `CYCLE`
- `CONTEXT`
- `PATTERN`
- `VECTOR`
- `TRAP`
- `RETEST`
- `TARGET_RISK`
- `TRIGGER`
- `SCALE_IN`
- `INVALIDATION`

Only `DATA`, `SESSION`, `CONTEXT`, and `TARGET_RISK` have partial coverage as flat features. Stages like `LOCATION`, `CYCLE`, `PATTERN`, `VECTOR`, `TRAP`, `RETEST`, and `TRIGGER` are still missing as typed tree stages.

## Required Next Artifacts

The next phase must create:

1. `rule_only_tree_baseline`
2. `typed_tree_gate_trace_schema`
3. `candidate_rejection_reason_catalog`
4. `manual_replay_annotation_template`
5. `long_short_separate_gate_baselines`
6. `regime_gate_baseline`

## Decision

Additional flat model training is blocked until the tree path is measured as deterministic gates.

The next approved research direction is not another generic model. It is a rule-only tree baseline and per-gate candidate audit.

## Promotion Boundary

Promotion remains blocked:

- `TRAIN_ADDITIONAL_FLAT_MODEL`
- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Artifacts

- Schema: `schemas/gc_tree_translation_gap_review.schema.json`
- Module: `trading_system/models/gc_tree_translation_gap_review.py`
- CLI: `tools/gc_tree_translation_gap_review.py`
- Validator: `tools/validate_phase56.py`
- Review: `configs/models/gc-tree-translation-gap-review.json`
- Tests:
  - `tests/models/test_gc_tree_translation_gap_review.py`
  - `tests/models/test_gc_tree_translation_gap_review_cli.py`
  - `tests/research/test_phase56_validator.py`

## Verification

```powershell
python -m pytest tests\models\test_gc_tree_translation_gap_review.py tests\models\test_gc_tree_translation_gap_review_cli.py tests\research\test_phase56_validator.py -q
python tools\validate_phase56.py
python -m py_compile trading_system\models\gc_tree_translation_gap_review.py tools\gc_tree_translation_gap_review.py tools\validate_phase56.py
```

Result:

- 4 tests passed.
- Phase 56 validator passed.
- Python compile check passed.
- Local path / secret scan found no matches.

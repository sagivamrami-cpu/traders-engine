# Phase 29 GC Label Split Policy Implementation Report

## Summary

Implemented a fail-closed GC label-contract and split/embargo policy candidate. The phase records the Codex recommendation under discussion: use outcome-contract labels instead of HHLL training targets, and use chronological walk-forward splits with purge/embargo instead of random split. It does not approve D7/D8; explicit human decision records are still required.

This phase does not build real labels, real splits, training rows, datasets, features, models, backtests, execution artifacts, broker actions, or capital-allocation artifacts.

## Files

- `configs/research/gc-label-split-policy.yaml`
- `schemas/gc_label_split_policy.schema.json`
- `trading_system/research/gc_label_split_policy.py`
- `tools/validate_gc_label_split_policy.py`
- `tools/validate_phase29.py`
- `tests/research/test_gc_label_split_policy.py`
- `tests/research/test_phase29_validator.py`

## Label Policy Candidate

- Primary label family: `OUTCOME_CONTRACT_LABEL`
- D7 decision status: `NEEDS_HUMAN_DECISION_RECORD`
- HHLL role: `AUXILIARY_DIRECTION_LABEL_ONLY_NOT_TRAINING_TARGET`
- HHLL auxiliary training status: `BLOCKED_PENDING_SEPARATE_PIT_LABEL_STUDY`
- Outcome labels must be future-only.
- Same-bar target and stop ambiguity remains `AMBIGUOUS_EXCLUDED_FROM_TRAINING`.
- Ambiguous labels must carry `LABEL_QUALITY_EXCLUDED_FROM_TRAINING_REQUIRED`.
- Binary projection remains `BLOCKED_PENDING_AMBIGUOUS_EXCLUSION_IMPLEMENTATION`.
- Allowed outcome classes: `TARGET_FIRST`, `STOP_FIRST`, `EXPIRED`, `AMBIGUOUS`.
- Target/stop thresholds remain `UNSPECIFIED_REQUIRES_GRAPH_TRADE_CONTRACT`.
- Max label horizon remains `UNSPECIFIED_REQUIRES_GRAPH_TRADE_CONTRACT`.
- Fill truth remains `UNSPECIFIED_REQUIRES_CONTRACT_IDENTITY_AND_COST_FILL_POLICY`.

## Split Policy Candidate

- Split method: `CHRONOLOGICAL_WALK_FORWARD_ONLY`
- D8 decision status: `NEEDS_HUMAN_DECISION_RECORD`
- `random_split_allowed=false`
- Purging required.
- Embargo required.
- Embargo size remains `PENDING_MAX_LABEL_HORIZON`.
- Purge rule remains `PENDING_MAX_LABEL_HORIZON`.
- Feature transforms must be fit only inside the train window.
- Known damaged 2017 aggressor window is applied identically to all dataset/model variants.
- Row-level 2017 mask remains `REQUIRED_NOT_IMPLEMENTED`.
- OHLCV-only vs order-flow scope remains `UNRESOLVED_REQUIRES_D8_DECISION`.

## Gates Preserved

- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `SESSION_CALENDAR`
- `ROLL_POLICY`
- `CONTRACT_IDENTITY`
- `GRAPH_TRADE_CONTRACT`
- `COST_FILL_POLICY`
- `MISSING_BAR_POLICY`
- `DATASET_IDENTITY`
- `CANONICAL_OHLCV_INPUT`
- `CANONICAL_ORDER_FLOW_INPUT`
- `ORDER_FLOW_SOURCE_DECISION`
- `ORDER_FLOW_ERA_MAP`
- `ROW_LEVEL_2017_MASK`
- `CUMULATIVE_FEATURE_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`

## Blocked Actions

- `BUILD_REAL_DATASET`
- `BUILD_REAL_LABELS`
- `BUILD_REAL_SPLITS`
- `TRAIN_PRODUCTION_MODEL`
- `USE_HHLL_AS_TRADE_CONTRACT_LABEL`
- `INGEST_HHLL_DERIVED_LABELS`
- `JOIN_HHLL_FILES_TO_TRAINING_ROWS`
- `USE_HHLL_AS_AUXILIARY_TRAINING_TARGET`
- `ADAPT_FIXTURE_TRADE_CONTRACT_TO_REAL_GC`
- `RANDOM_SPLIT_TIME_SERIES_ROWS`
- `BUILD_UNEMBARGOED_SPLITS`
- `USE_FIXTURE_WALK_FORWARD_POLICY`
- `USE_AMBIGUOUS_LABELS_FOR_TRAINING`
- `USE_BINARY_PROJECTION_WITH_AMBIGUOUS_AS_NEGATIVE`
- `INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES`
- `CLAIM_EDGE`
- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`

## Verification

- `python -m pytest tests\research\test_gc_label_split_policy.py -q`: PASS, 5 passed.
- `python -m pytest tests\research\test_phase29_validator.py -q`: PASS, 1 passed.
- `python tools\validate_phase29.py`: PASS, `Phase 29 artifacts validated`.

## Remaining Blockers

- Target/stop thresholds are not specified.
- Maximum label horizon is not specified.
- Numeric embargo and purge windows are not specified.
- Graph-specific trade contract is not approved.
- Contract identity and fill/cost policy are not approved.
- D7/D8 decision records do not exist yet.
- Row-level 2017 mask is not implemented.
- Upstream data gates remain unsatisfied.
- D1/D3 resolved `BAR_BOUNDARY`, `AVAILABLE_AT_POLICY`, and `TIMESTAMP_ROLE`; those gates are no longer carried here.
- Dataset construction remains blocked.
- Training remains blocked.

## Next

Claude Code accepted Phase 29 as a blocked candidate. Groq returned `ACCEPT_WITH_CHANGES`; Codex implemented the hardening by preserving D7/D8 decision-record blockers, adding fixture/HHLL/split side-door denials, requiring train-only fitting, and keeping row-level 2017 mask unimplemented.

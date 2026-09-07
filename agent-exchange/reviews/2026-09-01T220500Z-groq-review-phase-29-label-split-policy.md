# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T175001Z-groq-review-phase-29-label-split-policy.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T175001Z-groq-review-phase-29-label-split-policy.md`

Created at:
2026-09-01T22:05:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Challenge-review of the Phase 29 GC label-contract and split/embargo
policy candidate (config, schema, builder, CLI, validator, tests, report).
Review-only. This does not mark `LABEL_CONTRACT` or
`SPLIT_AND_EMBARGO_POLICY` satisfied. It does not answer human packet
D7–D8. It does not approve labels, splits, datasets, features, training,
promotion, live trading, broker execution, or capital allocation. No
vendor query. No raw rows included here.

Phase 29 is safe as a *blocked policy candidate* if Codex leaves
`LABEL_CONTRACT` and `SPLIT_AND_EMBARGO_POLICY` unsatisfied in Phase
24/25, does not copy D7/D8 recommendations into decision records, and
does not adapt `trading_system/candidates/labeling.py` or
`trading_system/datasets/splits.py` from this file. Construction, label
building, split building, and training are schema-const false. No
dataset/label/split builder imports this module.

It is not safe as D7/D8 approval, as a frozen outcome-contract recipe, as
permission to build labels or splits, or as an implemented 2017 mask.

Answers to the challenge focus:

- Worker reads this as permission to build labels, splits, a dataset, or
  a model: not from the four schema-const false flags or
  `BUILD_REAL_LABELS` / `BUILD_REAL_SPLITS` / `BUILD_REAL_DATASET` /
  `TRAIN_PRODUCTION_MODEL`. YES without F1–F2 wording, if the report’s
  “human-approved direction” plus D7’s “adapt the existing fixture label
  contract” is treated as go-ahead.
- HHLL as the primary training target: blocked in this payload (`hhll_role`
  const `...NOT_TRAINING_TARGET`; `USE_HHLL_AS_TRADE_CONTRACT_LABEL`).
  Still a later-path leak as an auxiliary loss head or via
  `INGEST_HHLL_DERIVED_LABELS`, which this `blocked_actions` list omits
  (F3).
- Same-bar target/stop ambiguity in training: excluded by policy string
  and `USE_AMBIGUOUS_LABELS_FOR_TRAINING`. `AMBIGUOUS` remains in
  `allowed_outcome_classes`. 4-class or fixture
  `binary_projection_allowed` can still train on it (F4).
- Random split: schema-const blocked. Non-embargoed chronological split:
  YES via existing `splits.py` / `walk-forward-policy.yaml`; embargo size
  is `PENDING_MAX_LABEL_HORIZON` (F5).
- 2017 damaged-aggressor mask identical on every variant: policy string
  says yes. No row-level mask. `ROW_LEVEL_2017_MASK` is not a remaining
  gate. Phase 24 window status is still OF-features-only (F6).
- Target/stop thresholds, max horizon, graph trade contract, contract
  identity, fill truth: still unspecified in status strings. Not named as
  remaining gates except `ROLL_POLICY`. Fixture 2R/2-bar/zero-cost
  labeler still exists (F2, F7).
- `validate_phase29.py` actually asserts the above: asserts this
  payload’s strings and the four false flags. Does not assert Phase 24
  still lists the two gates, D7/D8 records absent, embargo size pending,
  fixture labeler unused, or negative schema cases (F8).

Findings:

## F1 — Severity: BLOCKING — report/plan freeze D7/D8 as “human-approved” while the packet is still unanswered

- File: `docs/implementation-reports/phase-29-gc-label-split-policy.md`
- Also: `docs/superpowers/plans/2026-09-01-phase-29-gc-label-split-policy.md`, `agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md`, `schemas/gc_label_split_policy.schema.json`
- Observed issue: Human packet D7 (outcome-contract labels, HHLL auxiliary, same-bar excluded) and D8 (chronological walk-forward, embargo, 2017 mask on every variant) remain `NEEDS_HUMAN_APPROVAL`. The packet says it is not itself approval and requires decision records. No `agent-exchange/decisions/` file exists for D7 or D8. Schema still const-locks `primary_label_family`, `hhll_role`, `same_bar_target_and_stop_policy`, `split_method`, `random_split_allowed`, embargo/purge booleans, and the 2017 window. Report summary: “records the human-approved direction.” Plan architecture: “approved direction from the human conversation.” YAML `status` is correctly `POLICY_CANDIDATE_NOT_GATE_SATISFIED`. Same freeze pattern as Groq Phase 28 F1 (D1/30m/`available_at`).
- Risk: Codex or a later worker writes D7/D8 decision records from this schema, or marks `LABEL_CONTRACT` / `SPLIT_AND_EMBARGO_POLICY` satisfied because “Phase 29 locked the recipe.”
- Concrete failing scenario: After this review is filed, a worker removes those two names from Phase 24 `required_unsatisfied_gates` and adapts `label_long_candidate()` to GC 30m because D7’s meaning-if-approved says the fixture contract can be adapted later.
- Recommended fix / safer wording: Keep both gates unsatisfied. Do not cite this file as D7 or D8. Rewrite report/plan to “Codex recommendation candidate only; human packet unanswered; no decision record.” Do not create D7/D8 records from this phase.
- Blocks treating Phase 29 as D7/D8 approval or as those two gates SATISFIED: YES.
- Blocks keeping it as a blocked candidate: NO, if gates and Phase 24 lists stay.

## F2 — Severity: BLOCKING — family/method consts can close the gates while thresholds, horizon, graph contract, and fill truth stay unspecified

- File: `schemas/gc_label_split_policy.schema.json`
- Also: `configs/research/gc-label-split-policy.yaml`, `configs/datasets/gc-30m-real-dataset-contract.yaml`, `configs/contracts/label-contracts.yaml`
- Observed issue: Phase 24 `label_contract.required_decision` is still `OUTCOME_CONTRACT_LABEL_AT_SELECTED_TIMEFRAME` with `status: UNSATISFIED`. Phase 29 const-locks that family and the walk-forward method. Thresholds/horizon remain `UNSPECIFIED_REQUIRES_GRAPH_TRADE_CONTRACT`. Fill truth remains `UNSPECIFIED_REQUIRES_CONTRACT_IDENTITY_AND_COST_FILL_POLICY`. Embargo size remains `PENDING_MAX_LABEL_HORIZON`. `required_remaining_gates` names `LABEL_CONTRACT` and `SPLIT_AND_EMBARGO_POLICY` but not `GRAPH_TRADE_CONTRACT`, `COST_FILL_POLICY`, or `CONTRACT_IDENTITY` (only `ROLL_POLICY`). Fixture trade contract is still 2R, bar-low stop, `max_holding_bars=2`, zero commission, `live_thresholds_approved: false`.
- Risk: Gate resolution is “primary family chosen” rather than “executable label contract exists.” Invented 2R/2-bar labels become the GC training target.
- Concrete failing scenario: Worker copies `build_fixture_trade_contract()` onto resampled 30m GC bars. Same-bar high/low both touch. `AMBIGUOUS` rows are either dropped or trained as a fourth class. No graph-specific invalidation, no cost/fill, no contract identity.
- Recommended fix: Keep both gates unsatisfied until a D7/D8 record exists *and* numeric target/stop/horizon plus named graph contract plus fill/cost identity are explicit. Add unsatisfied fields or remaining-gate names for `GRAPH_TRADE_CONTRACT` and `COST_FILL_POLICY`. Add blocked action `ADAPT_FIXTURE_TRADE_CONTRACT_TO_REAL_GC`. Do not invent thresholds here.
- Blocks treating LABEL/SPLIT gates as satisfied from this candidate: YES.
- Blocks blocked-candidate acceptance: NO if those gates stay.

## F3 — Severity: HIGH — HHLL is not primary here; auxiliary and parallel ingest paths remain

- File: `configs/research/gc-label-split-policy.yaml`
- Also: `trading_system/research/databento_gc_source_profile.py`, `configs/datasets/gc-30m-real-dataset-contract.yaml`
- Observed issue: This payload cannot set HHLL as `primary_label_family`. `USE_HHLL_AS_TRADE_CONTRACT_LABEL` is blocked. `INGEST_HHLL_DERIVED_LABELS` is blocked in the Phase 20 source profile, not in this `blocked_actions` list. `hhll_role` is still an auxiliary *label* role. Phase 20 `hhll_label_role` is the weaker `AUXILIARY_DIRECTION_LABEL_ONLY` without `NOT_TRAINING_TARGET`. `hhll_*` files remain on disk as derived products.
- Risk: Multi-task training uses HHLL LONG/SHORT as a second head. Or a builder joins `hhll_*` because this phase did not repeat `INGEST_HHLL_DERIVED_LABELS`. Prior Groq vendor-plan F2: `L8R8` is commonly a right/future window.
- Concrete failing scenario: 30m outcome-contract model is selected because it tracks 4H HHLL direction; that direction is added to the loss.
- Recommended fix: Keep `USE_HHLL_AS_TRADE_CONTRACT_LABEL`. Add `INGEST_HHLL_DERIVED_LABELS` / `JOIN_HHLL_FILES_TO_TRAINING_ROWS` to this blocked list, or union Phase 24 denials. Do not use `hhll_*` as any training target, including auxiliary heads, until a separate PIT label study exists.
- Blocks HHLL as primary *in this payload*: NO.
- Blocks later HHLL join/auxiliary-loss: YES unless denials are inherited.

## F4 — Severity: HIGH — `AMBIGUOUS` is a first-class outcome class; exclusion is a string, not a drop rule

- File: `schemas/gc_label_split_policy.schema.json`
- Also: `configs/contracts/label-contracts.yaml`, `trading_system/candidates/labeling.py`, `trading_system/evaluation/walk_forward.py`
- Observed issue: `allowed_outcome_classes` prefixItems lock `TARGET_FIRST`, `STOP_FIRST`, `EXPIRED`, `AMBIGUOUS`. Same-bar policy is `AMBIGUOUS_EXCLUDED_FROM_TRAINING` and `USE_AMBIGUOUS_LABELS_FOR_TRAINING` is blocked (good). Phase 29 does not mention `label_quality`. Fixture labeling already sets same-bar rows to `label_quality=EXCLUDED_FROM_TRAINING`. Fixture `binary_projection_allowed: true` can score `TARGET_FIRST` vs rest, putting same-bar ambiguity in the negative class. Walk-forward `included_rows()` drops `EXCLUDED_FROM_TRAINING` only if that field is populated.
- Risk: A later 4-class softmax trains on same-bar hits. Or binary projection treats them as not-target.
- Concrete failing scenario: GC 30m labeler copies fixture classes, omits `label_quality`, fits on all four. Same-bar path-dependent fills become “learned” edge.
- Recommended fix: Keep the recorded `AMBIGUOUS` class. Require `label_quality=EXCLUDED_FROM_TRAINING` (or equivalent drop) before any builder. Do not enable 4-class or binary projection in this phase. Do not treat the blocked-action string as an implemented filter.
- Blocks this version including ambiguous rows in a trainer: NO, no trainer exists.
- Blocks using allowed classes as a 4-class training spec: YES.

## F5 — Severity: HIGH — embargo/purge are required booleans; a non-embargoed chronological split already exists

- File: `trading_system/datasets/splits.py`
- Also: `configs/evaluation/walk-forward-policy.yaml`, `configs/datasets/fixture-dataset-policy.yaml`, `configs/research/gc-label-split-policy.yaml`
- Observed issue: `random_split_allowed` is const false and `RANDOM_SPLIT_TIME_SERIES_ROWS` is blocked (good). `split_method` is `CHRONOLOGICAL_WALK_FORWARD_ONLY`. `embargo_required` / `purging_required` are true, but `embargo_size_status` is `PENDING_MAX_LABEL_HORIZON` and no purge width exists. `assign_chronological_split()` is train/validation/test cutpoints with no embargo or purge. Fixture walk-forward is expanding windows of size 3/1 with no embargo. `fold_fit_scope` is `FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_OR_VALIDATION_WINDOW` — not train-only. Fitting scalers on validation leaks into test. `blocked_actions` has no `BUILD_UNEMBARGOED_SPLITS` / `USE_FIXTURE_WALK_FORWARD_POLICY`. `_blocked_reasons` has no embargo-size reason.
- Risk: Worker ships “chronological walk-forward” using `splits.py` and calls embargo done because the boolean is true. Embargo of size 0. Label horizon overlaps the next fold.
- Concrete failing scenario: Max holding is later set to N 30m bars. Validation starts at the next bar after train_end. Outcomes from train labels are determined inside validation. Apparent edge is overlap.
- Recommended fix: Keep `SPLIT_AND_EMBARGO_POLICY` unsatisfied until horizon exists and embargo >= that horizon is numeric. Safer fit scope: `FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW`. Do not reuse fixture WF sizes. Optionally add `EMBARGO_SIZE_UNSPECIFIED` to `blocked_reasons`.
- Blocks random split in this payload: NO.
- Blocks implementing splits from this candidate: YES until size and purge are explicit.

## F6 — Severity: HIGH — 2017 “apply identically” is not a mask; Phase 24/27 still unimplemented

- File: `configs/research/gc-label-split-policy.yaml`
- Also: `configs/datasets/gc-30m-real-dataset-contract.yaml`, `agent-exchange/decisions/2026-09-01T153801Z-human-gc-order-flow-2017-exclusion.md`, `trading_system/research/gc_order_flow_availability_era_policy.py`
- Observed issue: `damaged_2017_mask_policy` is const `APPLY_IDENTICALLY_TO_ALL_DATASET_AND_MODEL_VARIANTS`. Window matches gates: `[2017-01-01T00:00:00Z, 2017-06-01T00:00:00Z)`. Human record is exclusion for paths that *use affected order-flow features*, and is not the complete era map. Phase 24 window status is `EXCLUDE_FROM_ORDER_FLOW_FEATURES` (no all-split-variants). Phase 27 `row_level_mask_status` is `REQUIRED_NOT_IMPLEMENTED`. Phase 29 remaining gates omit `ROW_LEVEL_2017_MASK`. No filter is implemented. Tests never apply a mask.
- Risk: OHLCV-only variants keep 2017 H1 while OF variants drop it, or the reverse. Comparison across variants is confounded. File-level drop is treated as the mask.
- Concrete failing scenario: Price-only model trains through 2017 H1. OF model drops the calendar window but still inherits archived `cvd` that crossed the damage. Both cite this policy.
- Recommended fix: Keep `ROW_LEVEL_2017_MASK` / `ORDER_FLOW_ERA_MAP` unsatisfied. Do not implement filtering here. Name the OHLCV-only vs OF-using scope as unresolved (human record is OF-conditional; D8 recommendation is all variants). Do not close `SPLIT_AND_EMBARGO_POLICY` from the slogan.
- Blocks treating the mask as applied: YES.
- Blocks recording the known window as a candidate control: NO.

## F7 — Severity: HIGH — fill/contract identity stay strings; fixture zero-cost fills are the live labeler

- File: `trading_system/candidates/labeling.py`
- Also: `configs/execution/cost-fill-policy.yaml`, `configs/candidates/fixture-graph-rules.yaml`
- Observed issue: `fill_truth_status` const requires contract identity and cost/fill policy. Cost-fill YAML is still `SPECIFICATION_FREEZE_DRAFT` with `touch_price_is_fill: false`. Fixture labeler sets `filled=True`, `realized_slippage_ticks=0.0`, `commission=0.0`, close entry. Graph id `tr-vshape-retest-long` is the only allowed research graph in the priority register. Phase 29 never names that graph and never says fixture-only. Continuous/stitched GC remains forbidden as fill/label truth from prior Groq D5 review; this blocked list omits `INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES`.
- Risk: “Outcome contract” is implemented as fixture close-fill 2R on a continuous GC series. Execution labels do not match any dated contract.
- Concrete failing scenario: Labels use close-as-fill on stitched front-month. Live GC.FUT or dated contract fills diverge; claimed edge is fill fiction.
- Recommended fix: Keep fill/identity unspecified. Do not call the fixture labeler from any GC path. Union Phase 24 denials including `INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES`. Do not invent costs.
- Blocks this version emitting real fills/labels: NO, flags are false.
- Blocks adapting the fixture labeler as GC fill truth: YES.

## F8 — Severity: MEDIUM — validator asserts this JSON, not the challenge meaning; YAML flags are not schema-locked

- File: `tools/validate_phase29.py`
- Also: `trading_system/research/gc_label_split_policy.py`, `tests/research/test_gc_label_split_policy.py`
- Observed issue: Validator checks report status, four false flags, primary family, HHLL role, same-bar string, walk-forward method, `random_split_allowed`, `embargo_required`, 2017 mask policy string, three remaining gates, six blocked actions, six blocked reasons, and no `C:\` / `/Users/` in stdout. It does not assert `future_only_outcome_required`, `purging_required`, `embargo_size_status`, threshold/horizon/fill status strings (only derived reasons), `BUILD_REAL_DATASET`, Phase 24 still listing the two gates, window dates, or negative schema tests (HHLL as primary, `training_allowed: true`, random split true). `_build_payload_body` hardcodes the four booleans false, then `load_gc_label_split_policy()` returns the original YAML, whose booleans are not schema-const. Tests do not fail if YAML says `label_building_allowed: true`. Remaining-gate list is thinner than Phase 24 (omits `MISSING_BAR_POLICY`, `DATASET_IDENTITY`, canonical inputs, `ORDER_FLOW_SOURCE_DECISION`, `ROW_LEVEL_2017_MASK`). `blocked_actions` is thinner than Phase 24/25 (no 4H/HHLL ingest, CVD, macro, XAUUSD/GLD, continuous series).
- Risk: After “Phase 29 validated,” a worker loads YAML as the API or treats the validator as proof that D7/D8 and the mask are done.
- Recommended fix: Assert embargo-size pending and Phase 24 still UNSATISFIED for the two gates. Add one negative schema test each for HHLL-as-primary and `random_split_allowed: true`. Do not export `load_gc_label_split_policy()` as a construction API. Optionally union Phase 24 denials.
- Blocks this version enabling construction/training: NO, report consts hold.
- Blocks using a green validator as D7/D8 or mask-applied evidence: YES.

Open questions:

- Codex: do not mark Phase 24/25 `LABEL_CONTRACT` or `SPLIT_AND_EMBARGO_POLICY` satisfied from Phase 29.
- Codex: do not treat this file as D7 or D8. The human packet remains unanswered; write decision records only after an explicit human reply.
- Codex: do not adapt `label_long_candidate()` / fixture 2R/2-bar/zero-cost fills to real GC.
- Codex: do not implement splits from `splits.py` or fixture walk-forward as the GC embargo policy.
- Codex: `ROW_LEVEL_2017_MASK` remains unimplemented; this slogan is not the mask.
- Human: D7 (outcome-contract vs HHLL, same-bar exclusion, still no numeric target/stop/horizon) and D8 (walk-forward + embargo size + 2017 scope on OF-only vs all variants) still need decision records before any label/split builder.

Recommended next action:

Accept Phase 29 only as a blocked label/split *candidate*. Carry F1–F7. Do not invent thresholds, embargo bars, or fills. Do not build labels, splits, datasets, or models. Next non-training work may stay on timestamp evidence and contract-identity profiling, or harden here (pending tokens on D7/D8, embargo-size reason, Phase 24 denial union, negative tests). Do not skip D7–D8.

Whether Codex may accept this phase as a blocked policy candidate only:
YES, with F1–F7 carried. NO as D7–D8, as LABEL/SPLIT gate completion, as an implemented 2017 mask, or as a label/split/training path.

Blocking-issue statement:

Blocking issues WERE found for treating outcome-contract / walk-forward consts as D7/D8 approval (F1) and for closing `LABEL_CONTRACT` / `SPLIT_AND_EMBARGO_POLICY` while thresholds, horizon, graph trade contract, and fill truth stay unspecified (F2). No issue found that currently sets `dataset_construction_allowed`, `label_building_allowed`, `split_building_allowed`, or `training_allowed` true, or that implements a labeler, splitter, or 2017 row mask in this module.

Verification reviewed:

- `python tools/validate_phase29.py`: PASS (`Phase 29 artifacts validated`). Passing tests do not cover F1–F8. No product files were modified.

Notes:
- Review-only: no product code edited, no vendor APIs, no raw rows, no commit/push.
- Independent of the Claude Code Phase 29 ACCEPT; F1–F7 are the challenge disagreements (human-approval freeze, fixture side doors, embargo-less chronological split, unimplemented 2017 mask, validation-window transform fit).
- No secrets, keys, account identifiers, raw market data, or absolute local paths are included here.

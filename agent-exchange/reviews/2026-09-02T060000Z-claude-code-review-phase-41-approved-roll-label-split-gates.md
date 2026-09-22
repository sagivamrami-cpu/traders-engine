# Agent Exchange Review

Reviewer:
Claude Code

Target request:
agent-exchange/inbox/claude-code/2026-09-02T053500Z-claude-code-review-phase-41-approved-roll-label-split-gates.md

Request:
agent-exchange/inbox/claude-code/2026-09-02T053500Z-claude-code-review-phase-41-approved-roll-label-split-gates.md

Created at:
2026-09-02T06:00:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_NOTES

Findings:

F1 (note, non-blocking): Four gates were removed relative to the accepted
post-Phase-39 state, not three. The Phase 39 Claude review
(`agent-exchange/reviews/2026-09-02T041500Z-claude-code-review-phase-39-row-mask-cumulative-policy.md`)
recorded the contract gate list as exactly eight: SESSION_CALENDAR,
MISSING_BAR_POLICY, ROLL_POLICY, DATASET_IDENTITY, ORDER_FLOW_SOURCE_DECISION,
LABEL_CONTRACT, SPLIT_AND_EMBARGO_POLICY, DATASET_CONSTRUCTION_AUTHORIZATION.
The contract now lists four. Phase 41 therefore also closed
ORDER_FLOW_SOURCE_DECISION (wired to D6-final,
`agent-exchange/decisions/2026-09-02T052003Z-human-d6-final-order-flow-source-decision.md`,
reflected in `source_decisions.order_flow_source_decision:
APPROVED_RESEARCH_ORDER_FLOW_SOURCE_V1` and the updated decisions YAML entry),
but the Phase 41 result and report name only ROLL_POLICY, LABEL_CONTRACT, and
SPLIT_AND_EMBARGO_POLICY as closed. The D6 closure is substantively authorized
(human-approved decision record, covered by the accepted Phase 40 recheck), so
this is a record-keeping gap, not an unauthorized gate removal. Codex should
amend the Phase 41 record (or a follow-up status note) to state explicitly that
ORDER_FLOW_SOURCE_DECISION was also closed by D6-final in this phase.

F2 (note, non-blocking): The blocker string
`ORDER_FLOW_SOURCE_DECISION_MUST_REMAIN_OPEN_FOR_CONTRACT_ONLY_PHASE` in
`trading_system/research/gc_real_dataset_contract.py` (`_decision_blockers`)
is now stale in name: with the decision APPROVED it correctly no longer fires,
but its semantics ("must remain open") describe the finished contract-only
phase. Cosmetic; consider renaming in a later phase so a future regression to
DEFERRED does not produce a misleading reason string.

F3 (note, non-blocking): D5-final requires that dataset manifests and model
cards carry `contract_identity_status: UNDECLARED_PENDING_RESEARCH`. The
contract carries `roll_policy.contract_identity` and
`roll_policy.model_card_contract_identity_status` as schema-pinned constants,
which satisfies the caveat at the contract level. No dataset manifest or model
card exists yet (correctly, since construction is blocked); the caveat must be
re-verified when the DATASET_IDENTITY gate work introduces those artifacts.

Review focus verification:

1. Gates newly removed: ROLL_POLICY, LABEL_CONTRACT, and
   SPLIT_AND_EMBARGO_POLICY are removed as requested, plus
   ORDER_FLOW_SOURCE_DECISION (see F1). No other gate was removed: the four
   remaining contract gates (SESSION_CALENDAR, MISSING_BAR_POLICY,
   DATASET_IDENTITY, DATASET_CONSTRUCTION_AUTHORIZATION) are enforced by
   `contains` constraints in both `schemas/gc_real_dataset_contract.schema.json`
   and `schemas/gc_label_split_policy.schema.json`, and the readiness report
   appends REAL_DATASET_NOT_BUILT.

2. Roll policy caveat: PRESERVED. `roll_policy.contract_identity` and
   `roll_policy.model_card_contract_identity_status` are both
   `UNDECLARED_PENDING_RESEARCH`, pinned as schema constants, with
   `blocker_status: RESEARCH_CAVEAT_RECORDED_NOT_EXECUTION_TRUTH` and
   `continuous_or_stitched_gc_policy:
   PROFILE_STYLE_SANITIZED_AGGREGATES_ONLY_NON_INGESTABLE`. The decision ref
   points to D5-final.

3. Label policy vs D7-final: EXACT MATCH. Outcome-contract primary label
   (`OUTCOME_CONTRACT_LABEL`), risk unit `ATR_14_30M_CLOSED_BARS_AT_DECISION`,
   `target_multiple: 1.0`, `stop_multiple: 1.0`, `max_horizon_bars: 8`,
   `entry_availability: NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE`, same-bar
   ambiguity `AMBIGUOUS_EXCLUDED_FROM_TRAINING` (with binary projection only
   after ambiguous-row exclusion), HHLL restricted to auxiliary/non-primary in
   both the contract and the label/split policy, and fill truth marked
   `ZERO_COST_RESEARCH_SIMULATOR_ONLY_NOT_EXECUTION_TRUTH`. All values are
   schema constants, so drift fails validation.

4. Split policy vs D8-final: EXACT MATCH. `CHRONOLOGICAL_WALK_FORWARD_ONLY`,
   `random_split_allowed: false` (schema const), purging required with
   `PURGE_OVERLAPPING_8_BAR_LABEL_HORIZON`, `embargo_bars: 8` matching the max
   label horizon, `fold_fit_scope: FIT_TRANSFORMS_ONLY_INSIDE_TRAIN_WINDOW`,
   and the shared 2017 mask function
   `trading_system.research.gc_order_flow_row_mask_cumulative_policy.apply_gc_order_flow_training_mask`
   applied to all dataset and model variants with the half-open
   2017-01-01/2017-06-01 UTC window. Note: D8 says embargo is "at least" the
   max horizon; the schema pins exactly 8, which satisfies v1 but will need a
   schema change if the horizon or embargo grows.

5. Dataset construction and training remain BLOCKED. Confirmed at four layers:
   config (`dataset_construction_allowed: false`, `training_allowed: false`,
   `label_building_allowed: false`, `split_building_allowed: false`,
   `construction_authorized_by: []`), schema constants (`{"const": false}` /
   `maxItems: 0` in all three schemas, readiness `training_start_allowed`,
   `dataset_construction_allowed`, `model_promotion_allowed` all const false),
   builder code (report builders hardcode False regardless of input), and the
   live readiness run (status BLOCKED with the five expected gates). The
   existing D9-final record cannot bypass this: `construction_authorized_by`
   must stay empty and DATASET_CONSTRUCTION_AUTHORIZATION remains in the
   required gate lists.

6. Hygiene: PASS. The changed configs, schemas, and tests contain no raw
   market rows, secrets, account identifiers, or local absolute paths; the only
   archive references are repo-relative manifest refs plus SHA-256 digests, and
   the tests themselves assert the CLI outputs contain no absolute path
   prefixes.

Open questions:

- None blocking. F1 should be answered by a Codex record update naming the
  D6/ORDER_FLOW_SOURCE_DECISION closure as part of this phase (or citing where
  it was separately accepted).

Recommended next action:

Codex records the F1 clarification, then proceeds to the remaining gates
(SESSION_CALENDAR implementation, MISSING_BAR_POLICY resolution,
DATASET_IDENTITY) with dataset construction still blocked.

Verification reviewed:

- `python -m pytest tests\research\test_gc_label_split_policy.py
  tests\research\test_gc_real_dataset_contract.py
  tests\research\test_gc_pretraining_readiness.py -q`: PASS, `14 passed`.
- `python tools\validate_gc_label_split_policy.py --policy
  configs\research\gc-label-split-policy.yaml`: PASS. Emitted sanitized JSON;
  `required_remaining_gates` is exactly the four expected dataset gates;
  all label/split fields match D7/D8; every allowed/blocked flag false/true as
  required; `blocked_reasons: [UPSTREAM_DATASET_GATES_UNSATISFIED]`.
- `python tools\gc_pretraining_readiness.py --contract
  configs\datasets\gc-30m-real-dataset-contract.yaml --decisions
  agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist
  configs\research\real-data-readiness-checklist.yaml --training-policy
  configs\models\baseline-training-policy.yaml --groq-phase24-review
  agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md
  --groq-phase24-intake
  agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`:
  PASS. `status: BLOCKED`, `required_pretraining_gates` exactly
  `[SESSION_CALENDAR, MISSING_BAR_POLICY, DATASET_IDENTITY,
  DATASET_CONSTRUCTION_AUTHORIZATION, REAL_DATASET_NOT_BUILT]`,
  `real_data_satisfied_count: 6`, `real_data_open_count: 1`,
  `training_start_allowed: false`, `dataset_construction_allowed: false`,
  `blocking_reviews: []`.

Boundary statement:

Review-only. No source, config, schema, or test files were modified. No vendor
was queried. No raw market rows were read. This review contains no secrets,
raw data, account identifiers, or local absolute data paths.

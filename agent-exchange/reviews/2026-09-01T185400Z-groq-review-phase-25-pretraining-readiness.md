# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T133901Z-groq-review-phase-25-pretraining-readiness.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T133901Z-groq-review-phase-25-pretraining-readiness.md`

Created at:
2026-09-01T18:54:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Risk-review of the Phase 25 GC pre-training readiness gate (schema, module,
CLI, validator, tests, report, human decision packet). Review-only. This does
not approve dataset construction, training, promotion, live trading, broker
execution, capital allocation, or deployment. It does not answer D1–D9.

Phase 25 currently cannot report training-ready: `status` const `BLOCKED`,
`training_start_allowed` const false, `dataset_construction_allowed` const
false, `model_promotion_allowed` const false. Contract gates, `REAL_DATASET_NOT_BUILT`,
and `GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING` appear when the CLI is run
without extra flags. Readiness remains `BLOCKED` (`satisfied_count: 5`,
`open_count: 2`).

False-readiness still exists: an honor-system flag drops the Groq-review
blocker even for a BLOCKED review; `allowed_next_actions` advertises work;
payload denials are thinner than Phase 24; mode name says readiness.

Findings:

## F1 — Severity: BLOCKING — Groq-review blocker is an honor-system flag, not intake of an accepted review

- File: `tools/gc_pretraining_readiness.py`
- Also: `trading_system/research/gc_pretraining_readiness.py`, `schemas/gc_pretraining_readiness_report.schema.json`
- Observed issue: `--groq-phase24-review-present` is a boolean. If true, `GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING` is omitted. Schema `blocking_reviews` may be empty. Validator does not pass the flag (good). Anyone can. Presence of a review file is not Codex `ACCEPTED_BY_CODEX`. A BLOCKED Groq review would still clear the gate.
- Risk: The request requires pending Groq review to remain a visible blocker. The flag hides it without acceptance. Later workers treat Phase 25 as “reviews done.”
- Concrete failing scenario: Operator runs the CLI with `--groq-phase24-review-present` after this file exists, including if verdict is not accept-as-construction-authority. Report still `BLOCKED` (schema const), but the review line is gone and D9 looks like the last click.
- Recommended fix: Detect a specific review path *and* require a Codex intake status of `ACCEPTED_BY_CODEX` for that review. A `BLOCKED` / `ACCEPT_WITH_CHANGES` review must keep a visible blocker until Codex records acceptance of the required changes. Do not take a CLI boolean.
- Blocks treating Phase 25 as a training gate: YES until the flag is removed. Does not by itself enable `training_start_allowed` today (still const false).

## F2 — Severity: HIGH — `allowed_next_actions` advertises implementation during a blocked gate

- File: `schemas/gc_pretraining_readiness_report.schema.json`
- Observed issue: Prior profile/contract phases used `allowed_next_actions` `maxItems: 0`. Phase 25 enums `COLLECT_HUMAN_GATE_DECISIONS`, `PROCESS_PHASE24_EXTERNAL_REVIEWS`, `IMPLEMENT_ORDER_FLOW_ERA_MAP_PROFILER`. An era-map profiler can become a second reader of the OF archive. D6 says metadata-only and keep OF source open; the action name does not say that.
- Risk: A later worker treats the report as authorization to implement era mapping on raw rows, or as a path around OF source still being open.
- Recommended fix: Either empty `allowed_next_actions` or rename to `PROPOSE_METADATA_ONLY_ERA_MAP_GATE` with blocked actions `BUILD_ORDER_FLOW_FEATURES` and `USE_ARCHIVED_CVD_COLUMN`. Era map must not satisfy `ORDER_FLOW_SOURCE_DECISION`.
- Blocks keeping Phase 25 as a blocked aggregator: NO if restated. Blocks reading the current enum as OF-feature authority: YES.

## F3 — Severity: HIGH — Phase 25 denials are thinner than the contract it wraps

- File: `trading_system/research/gc_pretraining_readiness.py`
- Observed issue: `blocked_actions` are only `BUILD_REAL_DATASET`, `TRAIN_PRODUCTION_MODEL`, `CLAIM_EDGE`, `MODEL_PROMOTION`, `LIVE_TRADING`, `BROKER_EXECUTION`, `CAPITAL_ALLOCATION`. Missing vs Phase 24: `BUILD_ORDER_FLOW_FEATURES`, `BUILD_CVD_FEATURES`, `BUILD_MACRO_FEATURES`, `QUERY_OPTIONS_DATA`, `INGEST_ORDERFLOW_4H_CSV`, `USE_HHLL_AS_TRADE_CONTRACT_LABEL`. Missing vs this review of Phase 23/24: `USE_ARCHIVED_CVD_COLUMN`, `MAP_GC_TO_XAUUSD`, `MAP_GC_TO_GLD`.
- Risk: Operators read the “pre-training readiness” JSON as the live denial list and start OF/CVD/4H/options work because those strings are absent.
- Recommended fix: Union Phase 24 denials into this report. Keep construction/training/promotion false.
- Blocks the current const-false training flags: NO. Blocks using this report as the only denial list: YES.

## F4 — Severity: HIGH — human packet D1–D9 are Codex recommendations, not decisions

- File: `agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md`
- Also: schema const `human_decision_request` pointing at that inbox item
- Observed issue: Inbox status is `NEEDS_HUMAN_APPROVAL` and correctly says the inbox item is not itself approval. D1 already recommends UTC-fixed 30m bars and `available_at = bar_end_utc`. Phase 24 schema already const-locks related candidates (`TS_EVENT_INTERVAL_START`, `BAR_WINDOW_END_OR_STRICTER`, contract id embedding `30m`).
- Risk: A worker copies D1–D8 recommendations into decision records because Phase 25 “points at” the packet. Invented thresholds become architecture.
- Recommended fix: Keep the pointer as a request, not evidence. Do not satisfy any contract gate from this inbox file. Human answers still need `agent-exchange/decisions/` records with approver, timestamp, scope, decision, evidence.
- Blocks collecting human answers: NO. Blocks treating the packet as D1–D9 approval: YES.

## F5 — Severity: MEDIUM — report can never go green without a schema bump, but the name says readiness

- File: `schemas/gc_pretraining_readiness_report.schema.json`
- Observed issue: `status` const `BLOCKED`; `training_start_allowed` const false; `real_data_open_count` `minimum: 1`. Honest for this version. Mode is `GC_PRETRAINING_READINESS`. Training policy `min_train_rows: 2` / `min_validation_rows: 1` is fixture-scale if later reused as a real threshold.
- Risk: Version bump flips consts to true after F1’s flag was used. Or the name is cited as “readiness exists.”
- Recommended fix: Keep consts blocked until a later versioned report that cannot go true unless every inherited Phase 24 gate, era map, real dataset id, and accepted reviews are machine-checked. Do not reuse fixture row minima as production training policy.
- Blocks this version as a blocked aggregator: NO.

Open questions:

- Codex: this Groq Phase 24 implementation review is now present. Do not pass `--groq-phase24-review-present` as a substitute for intake. Verdict on Phase 24 is `ACCEPT_WITH_CHANGES`, not construction authority.
- Human: D1–D9 remain unanswered. Inbox is not approval.
- Codex: era-map work, if any, must stay metadata-only and must not satisfy OF source.

Recommended next action:

Keep Phase 25 as a blocked aggregator. Fix F1 before trusting `blocking_reviews`. Union Phase 24 denials (F3). Do not implement dataset construction, training, or promotion from this report. Do not treat D1–D9 recommendations as decided. Era-map follow-up, if routed, must be profile/metadata-only.

Blocking-issue statement:

Blocking issues WERE found for false readiness of the Groq-review gate (F1) and for using this report as a thinner denial list or as D1–D9 approval (F3, F4). No issue found that currently sets `training_start_allowed` true. The report does not imply model-training readiness if the consts hold.

Verification reviewed:

- `python tools/validate_phase25.py`: PASS (`Phase 25 artifacts validated`). Validator does not exercise `--groq-phase24-review-present`.
- `python tools/validate_phase24.py`: PASS (chained).
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`: PASS. Status `BLOCKED`, `satisfied_count: 5`, `open_count: 2`.
- Databento live API: NOT RUN. No dataset, features, labels, or models were built.

Notes:

- No product code was edited.
- No human decision records were written.
- No secrets, raw market-data payloads, credentials, account identifiers, or
  absolute user paths are included here.

# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T172001Z-groq-review-phase-28-bar-session-timestamp-policy.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T172001Z-groq-review-phase-28-bar-session-timestamp-policy.md`

Created at:
2026-09-01T21:32:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Challenge-review of the Phase 28 GC bar/session/timestamp policy
candidate (config, schema, builder, CLIs, validator, tests, report).
Review-only. This does not mark `BAR_BOUNDARY`, `SESSION_CALENDAR`,
`TIMESTAMP_ROLE`, or `AVAILABLE_AT_POLICY` satisfied. It does not answer
human packet D1–D3. It does not approve resampling, dataset construction,
training, promotion, live trading, broker execution, or capital
allocation. No vendor query. No raw rows included here.

Phase 28 is safe as a *blocked policy candidate* if Codex leaves those
four gates plus `DATASET_CONSTRUCTION_AUTHORIZATION` unsatisfied in
Phase 24/25, does not copy `cme-globex-metals-research-v1` into
`session-calendar.yaml` or live GC metadata, and does not treat schema
consts as D1–D3. Construction and training are schema-const false.
`RESAMPLE_REAL_BARS` is in `blocked_actions`. No dataset builder imports
this module.

It is not safe as frozen 30m training architecture, as a complete CME
session calendar, as confirmed timestamp/`available_at` policy, or as
permission to detect OHLCV gaps or resample.

Answers to the challenge focus:

- UTC-fixed 30m treated as frozen training architecture before approval:
  YES without F1 wording. Values are schema-const; only status strings
  say candidate. Human 30m record is still candidate-only. D1 is still
  unanswered.
- CME normal-session hours treated as a complete calendar without
  holiday/maintenance overlay: YES without F2 wording. `calendar_id`
  drops `pending`. Daily break can be read as maintenance-done.
  `holiday_overlay_status` is the real guard and must stay
  `REQUIRED_NOT_ENCODED`.
- Timestamp policy treated as confirmed despite pending vendor evidence:
  YES for OHLCV 1s (`TS_EVENT_INTERVAL_START` is a positive const). NO
  for order-flow minute / naive-minute (those strings still require
  evidence). Parent status is correctly
  `PENDING_HUMAN_CONFIRMATION_AND_VENDOR_EVIDENCE`.
- Real resampling, dataset construction, or training starting from this
  policy: not in this version (schema consts false; no consumer). YES as
  a later-worker path if YAML is used as a calendar or if Phase 24 gates
  are dropped after “Phase 28 accepted” (F4).

Findings:

## F1 — Severity: BLOCKING — schema consts freeze D1/30m/`available_at` while those gates stay unsatisfied

- File: `schemas/gc_bar_session_timestamp_policy.schema.json`
- Also: `configs/data/gc-bar-session-timestamp-policy.yaml`, `configs/datasets/gc-30m-real-dataset-contract.yaml`, `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`, `agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md`
- Observed issue: Report status is `POLICY_CANDIDATE_NEEDS_REVIEW` and bar-boundary status is `POLICY_CANDIDATE_NOT_GATE_SATISFIED` (good). The *values* are frozen: `candidate_timeframe`/`interval` const `30m`, `timezone` const `UTC`, `boundary_minutes` prefixItems `[0, 30]`, `interval_semantics` const half-open UTC, `available_at` const `BAR_END_UTC`. Phase 24 still has `bar_boundary.status: UNSATISFIED` with `required_decision: UTC_FIXED_OR_SESSION_ANCHORED_WITH_DST_RULE` and `available_at_policy.default_candidate: BAR_WINDOW_END_OR_STRICTER`. Phase 28 collapses that OR to UTC-fixed and drops `OR_STRICTER`. Human packet D1 (UTC-fixed 30m, `available_at = bar_end_utc`) is still `NEEDS_HUMAN_APPROVAL`. The 30m decision record is `APPROVED` only as a first baseline *candidate* and says it does not freeze a training timeframe.
- Risk: Later workers treat schema consts as architecture. Session-anchored bars are no longer representable without a schema bump. `BAR_END_UTC` is copied as D1/D3 resolution. Persistent 30m datasets start “because Phase 28 locked the recipe.”
- Concrete failing scenario: After this review is filed, a worker removes `BAR_BOUNDARY` / `AVAILABLE_AT_POLICY` from Phase 24 `required_unsatisfied_gates` because the consts match the D1 recommendation. Resample uses UTC 00/30 even on Globex halt-straddling slots.
- Recommended fix / safer wording: Keep the four gates unsatisfied. Do not cite this file as D1. Prefer `available_at: BAR_END_UTC_CANDIDATE_NOT_GATE_SATISFIED` or keep Phase 24’s `BAR_WINDOW_END_OR_STRICTER` as the unsatisfied candidate string. Do not collapse `UTC_FIXED_OR_SESSION_ANCHORED_WITH_DST_RULE` until a D1 decision record exists. Safer calendar/timeframe ids should keep `CANDIDATE` in the token.
- Blocks treating Phase 28 as D1 approval or frozen 30m training architecture: YES.
- Blocks keeping it as a blocked candidate: NO, if gates and Phase 24 lists stay.

## F2 — Severity: BLOCKING — `cme-globex-metals-research-v1` plus encoded hours can be read as a complete Globex calendar

- File: `configs/data/gc-bar-session-timestamp-policy.yaml`
- Also: `schemas/gc_bar_session_timestamp_policy.schema.json`, `configs/data/databento-gc-source-metadata.yaml`, `configs/data/session-calendar.yaml`, `configs/data/source-inventory.yaml`
- Observed issue: Live GC metadata still uses `cme-globex-metals-research-pending-v1`, which is absent from `session-calendar.yaml` (only `us-equities-regular-v1` exists). Phase 28 const-locks `calendar_id: cme-globex-metals-research-v1` — the exact D2 approval name from the unanswered human packet — and encodes Sunday–Friday 17:00/16:00 CT plus a 16:00–17:00 CT `daily_break`. Status `SOURCE_BACKED_CANDIDATE_HOLIDAY_OVERLAY_REQUIRED` and `holiday_overlay_status: REQUIRED_NOT_ENCODED` are the intended guards. Missing from the object: CME trade-date roll (Sunday 17:00 CT open is typically the next trade date, not Sunday), weekend halt as distinct from the daily break, early closes, holiday closures, DST-to-UTC membership of each 30m slot, RTH vs Globex. The two cited URLs are not parsed or tested. On the fetched `trading-hours.html` text, the NYMEX/COMEX Sunday 5:00 p.m.–Friday 4:00 p.m. CT / Mon–Thu 4:00–5:00 p.m. CT line sits under **ClearPort Hours**, not a GC Globex matching-hours table. The same page publishes 2026 Globex holiday schedules, trade-date notes, and early-close TAS notes (including Gold TAS) that are not encoded. Fetched `gold.contractSpecs.html` text did not include 17:00/16:00 hours. Daily break can be misread as “maintenance overlay is already in.”
- Risk: Worker copies `cme-globex-metals-research-v1` over `pending-v1` in source metadata, adds it to `session-calendar.yaml` with empty `holidays`/`early_closes` like the equity fixture, and treats D2 as done. UTC 30m slots during halt/holiday/weekend are labeled gaps (D4) or in-session features.
- Concrete failing scenario: Good Friday / Christmas / Sunday-open-for-Tuesday-trade-date windows are classified with normal 17:00–16:00 CT rules. Train rows include closed-session bars or drop true Globex hours as missing bars.
- Recommended fix / safer wording: Keep `holiday_overlay_status: REQUIRED_NOT_ENCODED`. Do not add this id to `session-calendar.yaml`. Do not replace `cme-globex-metals-research-pending-v1` in live metadata. Safer id: `cme-globex-metals-research-pending-v1` or `cme-globex-metals-normal-hours-candidate-holiday-overlay-required`. Name an explicit `trade_date_roll_status: REQUIRED_NOT_ENCODED` and `utc_ct_bar_membership_status: REQUIRED_NOT_ENCODED`. Cite ClearPort vs Globex vs GC-product hours as unresolved. Do not guess holidays.
- Blocks treating normal hours as `SESSION_CALENDAR` SATISFIED or as a resampling calendar: YES.
- Blocks a source-cited *candidate* that keeps overlay/roll unencoded: NO.

## F3 — Severity: HIGH — OHLCV `TS_EVENT_INTERVAL_START` looks confirmed; OF minute correctly does not

- File: `schemas/gc_bar_session_timestamp_policy.schema.json`
- Also: `configs/data/gc-bar-session-timestamp-policy.yaml`, `configs/datasets/gc-30m-real-dataset-contract.yaml`
- Observed issue: `timestamp_policy.status` is const `PENDING_HUMAN_CONFIRMATION_AND_VENDOR_EVIDENCE` (good). `order_flow_minute_role` is `MINUTE_START_REQUIRES_VENDOR_EVIDENCE` and naive minutes are `TREAT_AS_UTC_ONLY_AFTER_VENDOR_EVIDENCE` (good; matches prior Phase 23 L2). `ohlcv_1s_timestamp_role` is const `TS_EVENT_INTERVAL_START` with no pending marker. That is the D3 recommendation and the Phase 24 unsatisfied `required_inputs.ohlcv_1s` const. Prior Groq Phase 20 notes Databento *docs* say `ts_event` is interval start, and required confirmation against *this* archive. D3 remains unanswered. No `vendor_evidence_status: MISSING` field.
- Risk: Worker treats OHLCV 1s role as decided, aligns 30m `available_at` to bar-end from interval-start 1s bars, and only leaves OF timezone open. Off-by-one vs HHLL `bar_close_utc` or vs OF `minute` if evidence later disagrees.
- Concrete failing scenario: Resample uses 1s `ts_event` as start, sets `available_at` to start+30m, and joins OF minutes that are still naive. Labels leak one bar.
- Recommended fix: Keep parent status pending. Mirror OF wording for OHLCV, e.g. `TS_EVENT_INTERVAL_START_REQUIRES_VENDOR_EVIDENCE`, or add `ohlcv_1s_evidence: DATABENTO_DOCS_NOT_ARCHIVE_CONFIRMED`. Do not record a D3 decision from this phase.
- Blocks treating timestamp policy as confirmed: YES for OHLCV 1s as written. NO for OF minute/naive-minute strings.
- Blocks blocked-candidate acceptance: NO if `TIMESTAMP_ROLE` stays unsatisfied.

## F4 — Severity: HIGH — no current resample/train path; empty `blocked_reasons` and thin denials are the later side door

- File: `trading_system/research/gc_bar_session_timestamp_policy.py`
- Also: `tools/validate_phase28.py`, `schemas/gc_bar_session_timestamp_policy.schema.json`
- Observed issue: Builder hardcodes `dataset_construction_allowed`/`training_allowed` false. Schema consts match. `blocked_actions` includes `RESAMPLE_REAL_BARS`. No `trading_system/` consumer besides this module. `blocked_reasons` is always `[]`; schema has no `minItems`. Phase 28 denials omit Phase 24/25 items (`CLAIM_EDGE`, `BUILD_ORDER_FLOW_FEATURES`, `USE_ARCHIVED_CVD_COLUMN`, `MAP_GC_TO_XAUUSD`, `INGEST_ORDERFLOW_4H_CSV`, `INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES`). `load_gc_bar_session_timestamp_policy()` returns unvalidated YAML. `validate_phase28.py` does not assert `DATASET_CONSTRUCTION_AUTHORIZATION`, `RESAMPLE_REAL_BARS`, timestamp status, or that Phase 24 still lists the four gates. D4 says OHLCV gap detection stays blocked until session/bar/timestamp/`available_at` are explicit; Phase 28 does not mention `MISSING_BAR_POLICY`.
- Risk: After “Phase 28 accepted,” a worker loads the YAML as the calendar, implements gap-drop on the UTC 30m grid, or treats empty `blocked_reasons` as no blockers.
- Concrete failing scenario: Same as prior Groq D4 case: UTC 30m grid drops Globex maintenance/holiday hours as OHLCV gaps. Selection bias looks like quality policy.
- Recommended fix: Populate `blocked_reasons` from the five remaining gates plus `HOLIDAY_OVERLAY_REQUIRED` and `VENDOR_TIMESTAMP_EVIDENCE_PENDING`. Keep `RESAMPLE_REAL_BARS`. Do not start gap detection. Optionally union Phase 24 denials. Validate YAML independently or stop exporting the loader as a calendar API.
- Blocks this version enabling construction/training: NO, consts hold.
- Blocks using this YAML to resample or to implement D4 drops: YES.

## F5 — Severity: MEDIUM — UTC-fixed bars vs CT session membership is unnamed and is required before D4

- File: `configs/data/gc-bar-session-timestamp-policy.yaml`
- Observed issue: D1 recommendation says session info is metadata and must not shift v1 bar boundaries. That DST-stable grid still must *label* which 30m UTC slots are in-session. 17:00 CT is 22:00 or 23:00 UTC. Half-open `[start, end)` bars can straddle 16:00–17:00 CT. Claude Code L1 is this issue; it is not LOW relative to D4. Phase 24 required DST rule in the bar-boundary decision name. Phase 28 records both policies and does not name membership/straddle/drop-mark-keep.
- Risk: Gate resolution skips membership. Halt-straddling bars become features or false gaps.
- Recommended fix: Add an explicit unsatisfied field, e.g. `utc_bar_session_membership: REQUIRED_NOT_ENCODED`. Carry it into `BAR_BOUNDARY` + `SESSION_CALENDAR` resolution. Do not invent the rule here.
- Blocks candidate: NO. Blocks gap detection and resampling until named: YES.

## F6 — Severity: LOW — session clock fields are opaque strings; overlay later can drift

- File: `schemas/gc_bar_session_timestamp_policy.schema.json`
- Observed issue: `open_time_ct`/`close_time_ct`/`daily_break_*` are const strings `"17:00"` / `"16:00"`. Fine while locked. Holiday overlay entries will not inherit that lock unless structured.
- Recommended fix: When overlay is encoded (after a D2 record and official CME overlay evidence), use timezone-aware structured times. Not now.
- Blocks candidate: NO.

Open questions:

- Codex: do not mark Phase 24 `BAR_BOUNDARY`, `SESSION_CALENDAR`, `TIMESTAMP_ROLE`, or `AVAILABLE_AT_POLICY` satisfied from Phase 28.
- Codex: do not treat this file as D1–D3. The human packet remains unanswered.
- Codex: do not replace `cme-globex-metals-research-pending-v1` in source metadata with `cme-globex-metals-research-v1`.
- Codex: D4 gap detection remains blocked; this candidate is not a missing-bar calendar.
- Human: D1 (UTC-fixed vs session-anchored), D2 (calendar id + overlay), D3 (timestamp evidence) still need decision records before any resample.

Recommended next action:

Accept Phase 28 only as a blocked bar/session/timestamp *candidate*. Carry F1–F5. Do not encode guessed holidays. Do not resample, construct, or train. Next non-training work may be label-contract / split-embargo *candidates* with the same fail-closed pattern, or hardening here (pending tokens, `blocked_reasons`, membership field). Do not skip D1–D3.

Whether Codex may accept this phase as a blocked policy candidate only:
YES, with F1–F5 carried. NO as D1–D3, as frozen 30m architecture, as a complete session calendar, as confirmed timestamps, or as a resample/gap-detection/training path.

Blocking-issue statement:

Blocking issues WERE found for treating UTC-fixed 30m / `BAR_END_UTC` as approved architecture (F1) and for treating encoded CME normal hours as a complete session calendar (F2). No issue found that currently sets `dataset_construction_allowed` or `training_allowed` true, or that implements resampling.

Verification reviewed:

- `python tools/validate_phase28.py`: PASS (`Phase 28 artifacts validated`). Passing tests do not cover F1–F5. No product files were modified.

Notes:
- Review-only: no product code edited, no vendor APIs, no raw rows, no commit/push.
- CME pages were fetched as public HTML for source-backing challenge only; no market-data rows.
- No secrets, keys, account identifiers, raw market data, or absolute local paths are included here.

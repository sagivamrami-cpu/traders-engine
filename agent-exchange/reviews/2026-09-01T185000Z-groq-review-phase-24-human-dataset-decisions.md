# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T131101Z-groq-review-phase-24-human-dataset-decisions.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T131101Z-groq-review-phase-24-human-dataset-decisions.md`

Created at:
2026-09-01T18:50:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Challenge-review of the human-confirmed GC dataset-planning records before they
are treated as Phase 24 authority. Review-only. This does not write decision
artifacts, does not approve dataset construction, and does not approve
training, promotion, live trading, broker execution, capital allocation, or
deployment. Readiness remains `BLOCKED` (`satisfied_count: 5`, `open_count: 2`).

The five records are internally consistent *as narrowed constraints*, and they
match the committed YAML: OF source omitted (still open), options `DEFERRED`,
30m candidate-only, 2017 as one exclusion, macro per-source gated. They are not
safe if `Decision: APPROVED` tokens are copied onto checklist items, if the
options record is read as v1 OF/macro authorization, or if the 2017 window is
treated as the complete era map.

Answers to the requested questions:

- Top blockers that could make Phase 24 unsafe or misleading: F1–F5 below
  (APPROVED tokens, options-record v1 wording, missing OF license, incomplete
  era map, 30m name freeze).
- Accidental leakage through CVD, macro timestamps, HHLL, 4H CSV, resampling:
  still possible unless Phase 24 fail-closes those paths (F3, F6).
- Source-readiness boundaries for OF and options: OF profile-only is correctly
  not in YAML; options `DEFERRED` still shows as open. Wording in the options
  record can undo that (F2).
- Phase 24 fields that must be mandatory and fail-closed: listed under
  “Mandatory fail-closed fields.”
- Extra human decision before a contract-only skeleton: NO, if the skeleton
  cannot construct data. YES before any builder, OF feature, or 30m freeze.
  One short “both” confirmation is recommended and does not block the skeleton
  (F7).

Findings:

## F1 — Severity: BLOCKING — `Decision: APPROVED` on non-source records is still a hidden-approval token

- File: `agent-exchange/decisions/2026-09-01T153800Z-human-gc-order-flow-source.md`
- Also: `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`, `agent-exchange/decisions/2026-09-01T153804Z-human-macro-features-leakage-gated.md`
- Observed issue: OF intake, 30m candidate, and macro leakage-gate records all use `Decision: APPROVED`. Scopes correctly deny source/feature/training authority. Checklist YAML correctly omits `ORDER_FLOW_SOURCE_DECISION`. A later worker keys off the token, not the scope.
- Risk: Same pattern as the prior OF-decisions F1. Profile-only OF becomes SATISFIED. 30m becomes the frozen training bar. Macro gate-approval becomes v1 macro features.
- Concrete failing scenario: YAML grows `ORDER_FLOW_SOURCE_DECISION: APPROVED` with evidence pointing at the profile-only record. Phase 24 then sees a “human OF approval.”
- Recommended fix / safer wording: Keep the records. Do not copy them onto readiness items. If restated: OF record decision line should read `PROFILE_ONLY_NOT_SOURCE_APPROVED`. 30m record should read `CANDIDATE_ONLY_NOT_FROZEN`. Macro record should read `GATED_NOT_APPROVED_FOR_V1_FEATURES`.
- Blocks recording OF/30m/macro as SATISFIED checklist items: YES.
- Blocks a contract-only Phase 24 skeleton: NO.

## F2 — Severity: BLOCKING — options-defer record authorizes a v1 OF+macro pipeline in prose

- File: `agent-exchange/decisions/2026-09-01T153803Z-human-options-v2-deferred.md`
- Observed issue: Decision is `DEFERRED` (correct). Scope says the v1 model pipeline “should proceed with OHLCV, order-flow, and leakage-checked macro features only.” That is feature-construction language inside an options deferral.
- Risk: v1 is treated as OF+macro-approved because options were deferred. Macro record says the opposite (not approved for v1 construction). OF source remains open.
- Concrete failing scenario: Phase 24+ builds OF+macro “because options are v2 and v1 proceeds with OF and macro.”
- Recommended fix / safer wording: “`OPTIONS_SOURCE_DECISION=DEFERRED` to v2. Does not SATISFY the item. Does not approve OF features, macro features, options parent, options query, or v1 training. v1 remaining work is contract/gates only until those separate approvals exist.”
- Blocks the `DEFERRED` options YAML entry itself: NO.
- Blocks reading this record as v1 OF/macro go-ahead: YES.

## F3 — Severity: BLOCKING — 2017 exclusion is still not an era map; CVD can leak around it

- File: `agent-exchange/decisions/2026-09-01T153801Z-human-gc-order-flow-2017-exclusion.md`
- Also: `configs/data/gc-order-flow-quality-gates.yaml`
- Observed issue: Record says “2017-01-01 through 2017-05-31” and requires Phase 23 to measure full schema/availability eras before any feature build. Gates encode `end: 2017-06-01T00:00:00Z`. Phase 23 sampled at most five Parquet files and copied the YAML window. Archive files include a precomputed `cvd` column. Dropping calendar rows does not un-poison a running sum after the window.
- Risk: Contract treats the five-month window as the era policy. Pre-2017 aggressor/MBO unavailability stays in training. Archived CVD is joined as a feature.
- Recommended fix: Phase 24 must keep `ORDER_FLOW_ERA_MAP` required and unsatisfied. State interval semantics as half-open UTC `[start, end)`. Block `USE_ARCHIVED_CVD_COLUMN`. Require PIT, fold-local, era-gapped recompute before any CVD-family feature. Do not invent additional vendor cuts here.
- Blocks treating the 2017 record as complete OF exclusion: YES.

## F4 — Severity: HIGH — OF ZIP still has no distinct license/retention record

- File: `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- Also: `agent-exchange/decisions/2026-08-31T175804Z-human-databento-gc-license-retention.md`
- Observed issue: `RAW_DATA_STORAGE_LICENSE_APPROVAL` is SATISFIED for the purchased GC OHLCV ZIP. The OF archive is a second local bundle. Profile-only OF record does not create a license record. Metadata still says OF license requires confirmation after profile.
- Risk: Feature work reuses the OHLCV license as OF authority.
- Recommended fix: Do not satisfy OF source. Add a separate OF license/retention decision before any OF feature build. Profile-only intake can continue without it.
- Blocks contract-only skeleton: NO. Blocks OF feature construction: YES.

## F5 — Severity: HIGH — 30m is approved as a candidate; names still freeze it

- File: `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`
- Observed issue: Scope correctly keeps 30m as a candidate and 4H CSV as reference-only. Canonical construction should start from lower-timeframe (primarily 1m Parquet) after session/bar/timestamp/missing-bar/roll decisions. Phase 24 config id is still `gc-30m-real-dataset-contract`.
- Risk: Contract id, filename, and “first baseline” are read as the frozen training bar before resample recipe exists.
- Recommended fix: Keep `timeframe_status: CANDIDATE_ONLY_NOT_FROZEN`. Do not let the contract id satisfy session/bar/timestamp/roll. Persistent 30m datasets stay blocked until those gates are explicit.
- Blocks a candidate-only 30m field on a fail-closed contract: NO. Blocks freezing 30m as training architecture: YES.

## F6 — Severity: HIGH — 4H/HHLL/macro leakage is still a join away

- File: `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`
- Also: `agent-exchange/decisions/2026-09-01T153804Z-human-macro-features-leakage-gated.md`
- Observed issue: 4H CSV is reference/sanity-check. HHLL is not a trade-contract outcome. Macro is research-open and per-source gated, not a v1 feed. None of that prevents a silent join unless Phase 24 denials are schema-locked.
- Concrete failing scenario: 30m model is selected because it tracks 4H HHLL direction; that direction becomes the label. Or FOMC/as-revised prints are joined on wall-clock, not `available_at`.
- Recommended fix: Phase 24 must block `INGEST_ORDERFLOW_4H_CSV`, `JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS`, `USE_HHLL_AS_TRADE_CONTRACT_LABEL`, `BUILD_MACRO_FEATURES`, and `USE_REVISED_MACRO_SERIES`. No invented macro feed.
- Blocks the reference-only / macro-gated records themselves: NO, with those denials.

## F7 — Severity: MEDIUM — “both approved” is still ambiguous

- File: `agent-exchange/inbox/groq/2026-09-01T131101Z-groq-review-phase-24-human-dataset-decisions.md`
- Observed issue: Five records share the same minute. Repository state cannot show which two “clarified pending decisions” a chat message approved. Inbox messages are not approval; the five committed records are.
- Recommended fix: One short human confirmation listing the five filenames. Until then, treat the five records as the authoritative set and the chat message as non-authoritative.
- Blocks contract-only skeleton: NO.

Mandatory fail-closed fields for a Phase 24 skeleton (must exist, currently unsatisfied, cannot construct data):

1. `session_calendar`
2. `bar_boundary` (UTC-fixed vs session-anchored, DST rule)
3. `timestamp_role` per input, including vendor timezone proof for OF `minute`
4. `available_at` derivation
5. `missing_bar_policy` per feature family
6. `roll_policy` / contract identity (dated vs parent vs continuous vs unknown)
7. `ORDER_FLOW_SOURCE_DECISION` remains open
8. `ORDER_FLOW_ERA_MAP` (full availability/schema eras; 2017 is one window)
9. `cumulative_feature_policy` (PIT, fold-local, era-gap; deny archived CVD)
10. `label_contract` (not HHLL; not 4H CSV)
11. `split_and_embargo_policy` with 2017 mask applied to every variant
12. dataset identity (archive sha256s, config hashes, profile hashes, deterministic id)
13. `dataset_construction_allowed=false`, empty `construction_authorized_by`
14. options deferred / do-not-query; macro blocked pending per-source gates
15. canonical input files undeclared (`GC` vs `GCall` vs `GCext`; 1s ZIP vs 1m-from-ticks)

Open questions:

- Human: confirm by filename that the five 2026-09-01T153800Z-:04Z records are the approved set.
- Human/Codex: do not satisfy OF source from the profile-only record.
- Codex: wait for a distinct OF license/retention record before OF features, not before the skeleton.

Recommended next action:

Codex may keep or accept a *contract-only* Phase 24 skeleton that encodes the fields above as unsatisfied and cannot build data. Do not wait for another human decision to write that skeleton. Do not record `ORDER_FLOW_SOURCE_DECISION=APPROVED`. Do not freeze 30m. Do not allow macro or archived CVD in v1. Ask for a one-line confirmation of the five filenames when convenient.

Blocking-issue statement:

Blocking issues WERE found for treating this bundle as OF/macro/30m/training authority (F1–F3). No blocking issue for a fail-closed contract-only skeleton.

Verification reviewed:

- `python tools/validate_phase23.py`: PASS (`Phase 23 artifacts validated`).
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`: PASS. Status `BLOCKED`, `satisfied_count: 5`, `open_count: 2`. `ORDER_FLOW_SOURCE_DECISION` open; `OPTIONS_SOURCE_DECISION` `DEFERRED` and still open.

Notes:

- No product code was edited.
- No decision files were written.
- No secrets, raw market-data payloads, credentials, account identifiers, or
  absolute user paths are included here.

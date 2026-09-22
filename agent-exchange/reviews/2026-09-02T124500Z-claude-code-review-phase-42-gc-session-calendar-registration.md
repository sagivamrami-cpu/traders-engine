# Agent Exchange Review

Reviewer:
Claude Code

Target request:
agent-exchange/inbox/claude-code/2026-09-02T063000Z-claude-code-review-phase-42-gc-session-calendar-registration.md

Request:
agent-exchange/inbox/claude-code/2026-09-02T063000Z-claude-code-review-phase-42-gc-session-calendar-registration.md

Created at:
2026-09-02T12:45:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
REVISION_REQUESTED

Scope of the revision is narrow. The calendar registration itself, the
`resolve_session()` Globex model, the contract/schema/policy wiring, the
Databento `status` skip record, and the remaining-gate list are correct and
need no change. The revision is limited to F1 (red validator suite inside the
declared validator-update scope) and F2 (a D2-final constraint that is neither
implemented nor explicitly deferred by a human record). Both are cheap to
close; once closed this review converts to ACCEPT_WITH_NOTES with F3-F10 as
notes.

Findings:

Blocking findings first.

F1 (blocking): `tools/validate_phase29.py` fails and `tools/validate_phase30.py`
fails by chaining into it, so `tests/research/test_phase29_validator.py` and
`tests/research/test_phase30_validator.py` are red (`2 failed in 146.99s`).
First failing assertion is `validate_phase29.py:42`
(`policy must remain gated`: it requires label/split `status ==
POLICY_CANDIDATE_NOT_GATE_SATISFIED`, which Phase 41 changed to the
schema-pinned `APPROVED_LABEL_SPLIT_CONTRACTS_DATASET_GATES_REMAIN`). This
failure therefore pre-dates Phase 42 and was missed by the Phase 41
verification set and by my Phase 41 review; I am recording that explicitly.
Phase 42 nonetheless owns it now for two reasons: (a) `validate_phase29.py:120`
also requires `SESSION_CALENDAR` in `required_remaining_gates`, so Phase 42
adds a second stale assertion, and (b) the Phase 42 request lists "Phase
validator updates for 20/21/23/24/25/28" as in scope, and 29/30 were skipped
even though 24/25/28 were retargeted for exactly this kind of gate closure.
Required: retarget `validate_phase29.py` to the current approved label/split
state (mirroring what was done in `validate_phase24.py:76-90` and
`validate_phase25.py:56-72`, i.e. assert the closed gates are absent and the
remaining gates present), or freeze it as a historical snapshot in a way that
keeps the pytest wrapper green. Then run the full validator chain 29-37 and
both wrapper tests and record the result. Not caused by Phase 42 code, but the
suite must be green before Codex acceptance.

F2 (blocking until recorded): D2-final
(`agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md`)
constrains the implementation to "Encode normal Globex metals hours, daily
maintenance break, holidays, special hours, DST behavior, and required
overlays" and "Create a dated overlay/reconciliation table with source
attribution." Phase 42 encodes normal hours, the daily break, and DST only;
`holidays: []`, `early_closes: []`, `special_sessions: []`, and
`configs/data/gc-session-calendar-overlay-reconciliation-policy.yaml` still
carries `overlay_table_status: REQUIRED_NOT_IMPLEMENTED` and
`reconciliation_table_status: REQUIRED_NOT_IMPLEMENTED`. The construction
policy simultaneously declares `session_calendar_gate_status:
SATISFIED_RESEARCH_CALENDAR_V1` and lists `CALENDAR_OVERLAY_TABLE` and
`VALIDATOR_FOR_SESSION_MEMBERSHIP` under `required_next_evidence`. The later
skip record
(`agent-exchange/decisions/2026-09-02T061500Z-human-d2-final-databento-status-schema-skip.md`)
does defer "holiday gaps, and special-hour gaps" to the missing-bar policy and
dataset manifest gates, which is a defensible narrowing, but it does not
mention the overlay/reconciliation table, and D2-final's text was not amended.
Codex's reading (SESSION_CALENDAR v1 = normal hours + break + DST; holidays,
special hours, venue halts, and the overlay/reconciliation table move to
MISSING_BAR_POLICY scope) is reasonable, but it is a scope change to a human
constraint and must be recorded by the human, not inferred by tools. Required:
a short human decision record (or an explicit amendment to D2-final) stating
that the overlay/reconciliation table and holiday/special-hour encoding are
transferred out of SESSION_CALENDAR into the MISSING_BAR_POLICY / dataset
manifest gates, and that SESSION_CALENDAR v1 is satisfied by normal hours,
daily break, and DST. Alternatively, implement the table under Phase 42. Until
one of these exists, SESSION_CALENDAR closure is authorized in spirit but not
in record.

Non-blocking notes.

F3 (note): The registered calendar cites three upstream artifacts via
`source_strategy_ref`, `evidence_manifest_ref`, and
`overlay_reconciliation_policy_ref`, and all three still pin
`calendar_id: cme-globex-metals-research-pending-v1` as a schema const
(`schemas/gc_session_calendar_source_strategy.schema.json:37`,
`schemas/gc_cme_calendar_evidence_manifest.schema.json:35`,
`schemas/gc_calendar_overlay_reconciliation_policy.schema.json:39`), keep
`REGISTER_SESSION_CALENDAR` in `blocked_actions`, and report
`session_calendar_gate_status: UNSATISFIED_*`. Treating them as frozen phase
snapshots is acceptable and avoids churning their validators (31-37 pass), but
the registered calendar should not cite them as if current. Suggest a
`superseded_by: cme-globex-metals-research-v1` (or `snapshot_status`) note on
each, or a sentence in the Phase 42 report stating they are frozen Phase
31/34/36 snapshots.

F4 (note): `utc_bar_session_membership_status: IMPLEMENTED_RESEARCH_V1`
(`configs/data/gc-bar-session-timestamp-policy.yaml:22`) and
`bar_membership_rules.rule_status: IMPLEMENTED_RESEARCH_V1`
(`configs/data/gc-session-calendar-construction-policy.yaml:43`) overstate
what exists. Only the instant-level `resolve_session()` is implemented; it is
not called anywhere in `trading_system/` or `tools/` outside its own module,
there is no 30m-bar membership function, and the same policy file still lists
`UTC_30M_BARS_THAT_STRADDLE_CME_DAILY_BREAK` and
`SESSION_CLOSED_BARS_DROP_MARK_OR_KEEP_WITH_SESSION_FLAG` as open
reconciliation questions. Suggest a status such as
`INSTANT_RESOLVER_IMPLEMENTED_BAR_MEMBERSHIP_PENDING_MISSING_BAR_POLICY` so a
later reader does not assume bar-level membership is solved.

F5 (note, latent defect): Holiday handling in
`trading_system/data_foundation/sessions.py:80-103` is keyed on the local CT
calendar date, not on trade date. Verified by probing with
`holidays=("2026-09-07",)` (a Monday): Sunday 2026-09-06 22:00Z (17:00 CT,
trade date Monday) still resolves `in_session=True, is_open_boundary=True`;
Monday 17:00 CT (the trade-date-Tuesday open) resolves closed; Tuesday morning
resolves open. So a holiday entry removes the tail of one trade date and the
head of the next while leaving the holiday trade-date's Sunday-evening head
live. Currently latent because `holidays` is empty and the human deferred
holidays to the missing-bar policy, but the code path is reachable from
config. Recommend either raising `ValueError` in
`_resolve_cme_globex_daily_break` when `holidays`, `early_closes`, or
`special_sessions` are non-empty until overlay semantics are defined, or
defining holiday membership by trade date. Related: `early_closes` is loaded
but unused in both session models (pre-existing), and `special_sessions` is
not loaded at all.

F6 (note): Close-boundary semantics are half-open in the Globex model (at
exactly 16:00 CT, `in_session=False` and `is_close_boundary=True`;
`sessions.py:85,91,100`) but inclusive in the legacy `regular_intraday` model
(`sessions.py:125`, `<=`). The half-open choice is the right one for D1's
`HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE` semantics; the asymmetry across
models should be documented so the fixture calendar is not used as a
reference. Boundary flags use exact `time` equality, so a timestamp with any
sub-second offset (verified with 22:00:00.000001Z: `in_session=True,
is_open_boundary=False`) never flags a boundary; fine for grid-aligned bar
timestamps, worth one line in the docstring.

F7 (note): DST coverage. `tests/data_foundation/test_sessions.py` covers only
CDT (September 2026). I verified independently that CST resolves correctly
(2026-01-11 23:00Z = 17:00 CST open with trade date 2026-01-12; 2026-01-12
22:00Z = 16:00 CST close; 22:30Z in break; 23:00Z reopen with trade date
2026-01-13; Friday 2026-01-16 22:00Z close), and that the spring-forward
Sunday (2026-03-08 22:00Z) and fall-back Sunday (2026-11-01 22:00Z pre-open,
23:00Z open) resolve correctly. Since
`DST_SHIFT_OF_CT_SESSION_BOUNDARIES_AGAINST_UTC_BARS` is a listed open
question, add a CST case and both transition-Sunday cases to the test file so
this stays pinned.

F8 (note): Off-session states carry `session_id` / `trade_date` equal to the
local date (e.g. Saturday 2026-09-12 and Sunday pre-open 2026-09-06), which
are not real trade dates. Consumers must gate on `in_session`; consider a
sentinel or documenting this.

F9 (note): `configs/data/gc-order-flow-quality-gates.yaml:24` still lists
`SESSION_CALENDAR` under `timeframe.blocked_until_decided`. Stale relative to
the contract; harmless, but it will confuse a later gate audit.

F10 (note, positive): `tools/validate_phase1.py` was tightened from
`real-*`-prefixed sources to all non-fixture sources
(`non-fixture source is not open`), with a new negative test. This is a
strengthening, not a weakening. `configs/data/source-inventory.yaml` now
carries `session_calendar_id: cme-globex-metals-research-v1` on
`databento-gc-1s` while that source stays `OPEN_HUMAN_DECISION`; Phase 1 does
not validate calendar-id existence for non-fixture sources, which is
acceptable here because the id now exists.

Review questions, answered:

1. Closes only SESSION_CALENDAR relative to post-Phase-41 readiness: YES.
   Post-41 gates were exactly `SESSION_CALENDAR, MISSING_BAR_POLICY,
   DATASET_IDENTITY, DATASET_CONSTRUCTION_AUTHORIZATION` plus
   `REAL_DATASET_NOT_BUILT` in the readiness report (my Phase 41 review,
   item 1). The live readiness run now reports exactly the last four. The
   remaining three contract gates are pinned by `contains` in
   `schemas/gc_real_dataset_contract.schema.json` and
   `schemas/gc_label_split_policy.schema.json`; the timestamp-policy schema
   pins `MISSING_BAR_POLICY` and `DATASET_CONSTRUCTION_AUTHORIZATION`; the
   readiness schema pins `DATASET_CONSTRUCTION_AUTHORIZATION` and
   `REAL_DATASET_NOT_BUILT`. `validate_phase24.py` and `validate_phase25.py`
   assert `SESSION_CALENDAR` is absent from the gate lists. No other gate was
   removed. Subject to F2 for the authorization record.

2. Bounded as research-only, not execution truth: YES.
   `registration_status: RESEARCH_REGISTERED_V1_NOT_EXECUTION_TRUTH`,
   `research_limitations.execution_truth: false`,
   `observed_activity_authority: false` in `session-calendar.yaml`;
   `SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH` pinned as a schema
   const in both the contract and the timestamp policy;
   `USE_TRADINGVIEW_AS_AUTHORITY` and `QUERY_DATABENTO_STATUS_SCHEMA` in the
   construction policy's `blocked_actions`;
   `RESEARCH_ONLY_CALENDAR_NOT_EXECUTION_TRUTH` in `blocked_reasons`.

3. `resolve_session()` coherence for daily break, Sunday open, Friday close,
   DST via `America/Chicago`, trade-date roll: YES for the normal-hours
   template. Sunday >= 17:00 CT opens with trade date +1; Mon-Thu < 16:00 CT
   is the same-day trade date, 16:00-17:00 closed, >= 17:00 rolls to +1;
   Friday closes at 16:00 CT; Saturday closed; DST handled by `zoneinfo`
   (verified both directions, F7). Caveats: F5 (holiday semantics latent),
   F6 (half-open close), F4 (no bar-level membership yet).

4. All contracts/schemas keep construction, resampling, label/split building,
   training, promotion, live trading, broker execution, capital allocation
   blocked: YES. `dataset_construction_allowed`, `training_allowed`,
   `resampling_allowed`, `label_building_allowed`, `split_building_allowed`,
   readiness `training_start_allowed` / `dataset_construction_allowed` /
   `model_promotion_allowed` are all `const false`;
   `construction_authorized_by` is `maxItems: 0`; `construction_allowed:
   false` and `calendar_registration_allowed: true` are pinned in the
   construction-policy schema; `blocked_actions` in every touched policy
   still include `BUILD_REAL_DATASET`, `RESAMPLE_REAL_BARS`,
   `TRAIN_PRODUCTION_MODEL`, `MODEL_PROMOTION`, `LIVE_TRADING`,
   `BROKER_EXECUTION`, `CAPITAL_ALLOCATION`. Live readiness run: `BLOCKED`.

5. Databento `status` schema skip record consistent with D2-final and the
   no-API-query constraint: YES. D2-final required "Record a v1 skip decision
   for Databento `status` schema for this implementation path"; the record has
   approver, timestamp, scope, decision, constraints, and evidence. The
   no-query constraint is preserved in code paths: `QUERY_DATABENTO_STATUS_SCHEMA`
   remains blocked in the construction policy, the source strategy's
   `databento_status_leg` remains `BLOCKED_PENDING_SEPARATE_COST_SOURCE_APPROVAL`,
   and the record's ref is pinned as a schema const in the contract and the
   construction policy. No vendor query is present in the diff.

6. Unrelated gate accidentally removed or weakened: NO. `validate_phase1.py`
   was strengthened (F10). The only regression found is the stale validator
   suite (F1), which is a test defect, not a gate weakening.

7. Hygiene: PASS. No raw market rows, secrets, account identifiers, or local
   absolute data paths in the changed configs, schemas, tests, code, or
   exchange records. Only repo-relative refs and public CME URLs.

Open questions:

- F2: does the human intend SESSION_CALENDAR v1 to be satisfied by normal
  hours + daily break + DST alone, with the overlay/reconciliation table and
  holiday/special-hour encoding transferred to MISSING_BAR_POLICY scope? If
  yes, a decision record saying so closes F2. If no, Phase 42 is not complete.
- F1: should `validate_phase29.py` be retargeted (like 24/25/28) or frozen as
  a snapshot? Either is fine; the wrapper tests must pass.

Recommended next action:

Codex (1) fixes `validate_phase29.py` and reruns the 29-37 chain plus
`tests/research/test_phase29_validator.py` and `test_phase30_validator.py`,
recording the results; (2) routes F2 to the human as a one-paragraph decision
record; (3) optionally applies F3 (superseded note) and F4 (status wording)
in the same pass since they are text-only. After (1) and (2) I will re-check
and expect to convert this to ACCEPT_WITH_NOTES. Dataset construction and
training remain blocked throughout.

Verification reviewed:

- `python -m pytest tests\data_foundation\test_sessions.py
  tests\data_foundation\test_phase1_configs.py
  tests\research\test_gc_session_calendar_construction_policy.py
  tests\research\test_gc_bar_session_timestamp_policy.py
  tests\research\test_gc_real_dataset_contract.py
  tests\research\test_gc_pretraining_readiness.py
  tests\research\test_gc_label_split_policy.py
  tests\research\test_databento_gc_order_flow_profile.py::test_order_flow_profile_cli_outputs_sanitized_json
  tests\research\test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_cli_outputs_sanitized_json
  tests\research\test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_cli_outputs_sanitized_json -q`:
  PASS, `37 passed in 13.62s`. Matches Codex's claim.
- `python tools\validate_phase1.py`: PASS, `Phase 1 artifacts validated`.
- `python tools\validate_phase39.py`: PASS, `Phase 39 artifacts validated`.
- `python tools\gc_pretraining_readiness.py --contract
  configs\datasets\gc-30m-real-dataset-contract.yaml --decisions
  agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist
  configs\research\real-data-readiness-checklist.yaml --training-policy
  configs\models\baseline-training-policy.yaml --groq-phase24-review
  agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md
  --groq-phase24-intake
  agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`:
  PASS. `status: BLOCKED`; `required_pretraining_gates` exactly
  `[MISSING_BAR_POLICY, DATASET_IDENTITY, DATASET_CONSTRUCTION_AUTHORIZATION,
  REAL_DATASET_NOT_BUILT]`; `training_start_allowed: false`;
  `dataset_construction_allowed: false`; `model_promotion_allowed: false`;
  `blocking_reviews: []`; `real_data_satisfied_count: 6`,
  `real_data_open_count: 1`.
- Additional (beyond the request): `python tools\validate_phase{0..28}.py`:
  all PASS. `python tools\validate_phase37.py` (chains 36->35->34->33->32->31->28):
  PASS, `Phase 37 artifacts validated` (110s). `python tools\validate_phase38.py`:
  PASS.
- Additional (beyond the request): `python tools\validate_phase29.py`: FAIL,
  `ValueError: policy must remain gated` (line 42). `python
  tools\validate_phase30.py`: FAIL via chained `validate_phase29.py`.
  `python -m pytest tests\research\test_phase29_validator.py
  tests\research\test_phase30_validator.py -q`: FAIL, `2 failed in 146.99s`.
  See F1.
- Additional (beyond the request): read-only `resolve_session()` probes for
  CST, DST transition Sundays, sub-second boundary, off-session ids, and a
  synthetic Monday holiday. Results recorded in F5-F8. No files were modified
  by these probes.
- `git status --short` / `git diff` inspected for `sessions.py`,
  `session-calendar.yaml`, `validate_phase1.py`, `test_phase1_configs.py`,
  `source-inventory.yaml`, `symbol-map.yaml`. Note that HEAD is still at the
  Phase 19 commit, so the diff is cumulative from Phase 20 onward; no commit
  or push was performed by this review.

Boundary statement:

Review-only. No source, config, schema, or test files were modified; the only
file written is this review. No vendor was queried. No raw market rows were
read. Dataset construction and training are not approved by this review. This
review contains no secrets, raw data, account identifiers, or local absolute
data paths.

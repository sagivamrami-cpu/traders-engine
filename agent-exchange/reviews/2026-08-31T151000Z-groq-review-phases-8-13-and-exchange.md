# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-08-31T090000Z-groq-review-phases-8-13-and-exchange.md`

Created at:
2026-08-31T15:10:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
BLOCKING_ISSUES_FOUND

This is review-only. It does not approve data, model promotion, architecture,
live trading, broker execution, capital allocation, or deployment. Default
repository readiness remains `BLOCKED` with `satisfied_count: 0`. Blocking
issues still exist on the real-CSV path and on the human-approval boundary
before real-data decision intake should continue.

Findings:

## F1 — Severity: BLOCKING

- File: `configs/data/symbol-map.yaml`
- Also: `trading_system/features/market_state.py`, `trading_system/datasets/factory.py`, `trading_system/research/offline_dry_run.py`, `configs/data/local-csv-onboarding-template.yaml`
- Observed issue: The Phase 8–13 local-CSV path reuses fixture identity. The committed symbol map only maps `SPY` to `TR_FIXTURE_SPY`. Unified market-state snapshots hardcode `availability={"ohlcv-fixture-v1": True}` and `regime={"primary": "FIXTURE_NEUTRAL"}`. Training rows hardcode `dataset_id="fixture-candidate-dataset"`. Dry-run candidate generation is `generate_fixture_candidate`. The onboarding template’s canonical symbol is `TR_FIXTURE_SPY`. Inspection tests suggest `TR_REAL_SPY`, which cannot map through the current symbol map.
- Risk: The first real historical CSV named `SPY` would either fail onboarding (if metadata uses a real canonical symbol) or silently inherit fixture source, dataset, regime, and candidate-graph identity (if metadata copies the template). That is fixture contamination of real research evidence and a point-in-time/provenance failure.
- Recommended follow-up: Codex should require a scoped contract that forbids fixture IDs on any non-fixture CSV, requires an explicit real-symbol map entry before bundle acceptance, and fails dry-run if `source_id`, `dataset_id`, availability keys, or graph versions still say fixture.

## F2 — Severity: BLOCKING

- File: `trading_system/research/readiness.py`
- Also: `tools/real_data_readiness.py`, `agent-exchange/protocol.md`, `AGENTS.md`, `tests/research/test_real_data_readiness.py`
- Observed issue: Human approval is defined as records under `agent-exchange/decisions/` with approver, timestamp, scope, decision, and evidence. Readiness can mark items `SATISFIED` and emit `READY_FOR_PRODUCTION_DATASET` from any YAML passed to `--decisions`. The loader does not require evidence paths to exist, to live under `agent-exchange/decisions/`, or to be written by a human. `test_all_items_approved_yields_ready_status` already produces that ready status from a temporary YAML. Phase 14 also records explicit defer / local-only resolutions as `APPROVED`.
- Risk: Hidden production approval. An inbox message, a template copy, or an agent-authored YAML can satisfy production-dataset readiness without a human decision record. Encoding defer as `APPROVED` collapses “not using this feed” into the same token as vendor approval.
- Recommended follow-up: Codex should keep production-dataset construction blocked until readiness SATISFIED requires a resolvable `agent-exchange/decisions/` record, evidence-path existence, and a distinct defer token that cannot satisfy vendor/source approval items.

## F3 — Severity: HIGH

- File: `trading_system/data_foundation/normalization.py`
- Also: `configs/data/normalization-policy.yaml`, `trading_system/data_foundation/csv_inspection.py`, `tools/inspect_local_ohlcv_csv.py`
- Observed issue: Timestamp parsing uses the committed policy timezone (`America/New_York`) for naive timestamps. Metadata `timezone` is copied into the manifest and suggested metadata but is not used to parse. Inspection has no timezone flag. `available_at < observed_at` is not rejected; only delays above `stale_after_seconds` are marked STALE. Inspection date ranges use `timestamp` only and never read `available_at`.
- Risk: Point-in-time error. A UTC export treated as New York shifts every bar by several hours. A row whose `available_at` precedes `observed_at` is look-ahead in the source clock and still enters onboarding and dry-run. Inspection can report `READY_FOR_BUNDLE_VALIDATION` without seeing that.
- Recommended follow-up: Fail closed when metadata timezone disagrees with parse timezone; reject `available_at < observed_at`; include `available_at` in inspection; do not invent a new timezone — require an explicit human timezone decision per source.

## F4 — Severity: HIGH

- File: `tools/run_local_csv_dry_run.py`
- Also: `docs/implementation-reports/phase-11-local-source-bundle-validation.md`, `trading_system/research/source_bundle.py`
- Observed issue: Phase 11 says retention must pass before a dry-run summary is produced. That is true only inside `validate_local_source_bundle`. `tools/run_local_csv_dry_run.py` onboarded CSV plus metadata with no retention policy, no source-status gate, and no bundle check. Onboarding itself copies `source_status` from metadata and does not require `OPEN_HUMAN_DECISION`.
- Risk: The dry-run CLI is a bypass around the Phase 10/11 safety gate. A non-open or retention-blocked bundle can still emit a research-run payload, including `training_run.status` that may become `TRAINED` on a larger CSV.
- Recommended follow-up: Make the dry-run CLI refuse to run unless bundle validation status is `ACCEPTED_FOR_DRY_RUN`, or delete the independent dry-run entrypoint from the documented human flow.

## F5 — Severity: HIGH

- File: `trading_system/data_foundation/csv_inspection.py`
- Also: `schemas/local_csv_inspection_report.schema.json`, `tests/data_foundation/test_csv_inspection.py`
- Observed issue: Status `READY_FOR_BUNDLE_VALIDATION` is granted after row-count, header columns, and single-raw-symbol checks only. It does not check: empty `raw_symbol` values, symbol-map membership, canonical-symbol match, OHLC validity, duplicate timestamps, monotonic time, `available_at`, correction_status, session calendar, declared timeframe vs bar spacing, or required metadata fields beyond CLI defaults. Empty-symbol files (`raw_symbol` blank on every row) produce `raw_symbols=[]`, no suggested metadata, no blocked reason, and still `READY_FOR_BUNDLE_VALIDATION`.
- Risk: Humans and later tools can treat inspection green as bundle-ready. The suggested metadata also injects defaults (`EQUITY_ETF`, `LOCAL_CSV`, `1m`, `us-equities-regular-v1`) that can be copied into production metadata without a human decision on those fields.
- Recommended follow-up: Fail inspection on empty/blank symbols, unknown symbols, and missing available_at parse. Rename the green status or document it as “shape-only, not bundle-ready.” Do not emit suggested asset class, venue, timeframe, or calendar unless those values come from an explicit human input with no silent defaults.

## F6 — Severity: HIGH

- File: `schemas/real_data_readiness_report.schema.json`
- Also: `configs/research/real-data-readiness-checklist.yaml`, `trading_system/research/readiness.py`
- Observed issue: When every checklist item is SATISFIED, report `status` becomes `READY_FOR_PRODUCTION_DATASET` while `blocked_actions` still includes `BUILD_PRODUCTION_TRAINING_DATASET`, `TRAIN_PRODUCTION_MODEL`, and `MODEL_PROMOTION`. Independently, `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` have `required_before` of feature-build actions, but any open item blocks the whole report, so OHLCV-only research cannot become ready without those decisions. The workaround in Phase 14 is to mark defer as `APPROVED`.
- Risk: Consumers can read either field and get opposite answers. The status name implies production-dataset approval. Coupling unrelated brains into one ready/not-ready bit pushes operators toward fake `APPROVED` defers.
- Recommended follow-up: Keep overall status `BLOCKED` until a named, human-approved action is actually allowed. Gate order-flow/options separately. Do not use `READY_FOR_PRODUCTION_DATASET` while `BUILD_PRODUCTION_TRAINING_DATASET` remains a blocked action.

## F7 — Severity: HIGH

- File: `.gitignore`
- Also: `tools/inspect_local_ohlcv_csv.py`, `tools/onboard_ohlcv_csv.py`, `tools/validate_local_source_bundle.py`, `agent-exchange/README.md`
- Observed issue: `.gitignore` does not ignore `*.csv`, raw data roots, or user exports. Phase 8–13 tools print `csv_path` as a local filesystem path in JSON. Protocol forbids secrets, private identifiers, and raw market-data payloads in `agent-exchange/`. Nothing stops a human or agent from committing a real CSV or pasting tool JSON (with user paths) into inbox/status/reviews.
- Risk: Raw retention can happen through git even though the retention policy hard-blocks copy/upload. Path JSON can leak account/user directories. Once committed, that is undeclared production data in the repo.
- Recommended follow-up: Ignore raw CSV/export locations by default; teach CLIs to emit basename or a redacted path; add an exchange scan that rejects files containing raw OHLCV rows or absolute user paths.

## F8 — Severity: MEDIUM

- File: `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- Also: `docs/implementation-reports/phase-8-local-csv-onboarding.md`, `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`
- Observed issue: The architecture plan’s Phase 8 is “Optional Offline RL.” The implementation series Phase 8 is local CSV onboarding; Phases 9–13 are dry-run, retention, bundle, readiness, inspection. The operating-model spec still assigns Groq review to the architecture plan’s phase list (data foundation, features, labels, baselines). Codex inbox for this cycle cites both documents as if they share phase numbers.
- Risk: An implementer or reviewer can execute the wrong Phase 8. Groq review of “Phase 8” is ambiguous. Human operators cannot tell whether RL, real-data intake, or architecture-plan Phase 4 baselines are next.
- Recommended follow-up: Codex should publish an explicit phase-map decision: architecture-plan phases vs implementation-report phases. Do not leave both numbering schemes live without a legend.

## F9 — Severity: MEDIUM

- File: `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- Also: `tools/inspect_local_ohlcv_csv.py`, `agent-exchange/templates/review.md`, `tools/watch_agent_exchange.py`, `agent-exchange/protocol.md`
- Observed issue: Human verification uses `python tools/inspect_local_ohlcv_csv.py --input <local_csv_path>`. The CLI requires `--csv` plus `--source-id` and `--canonical-symbol`; `--input` does not exist. The review template has `Verdict:` not `Status:`; the watcher only extracts `Status:`. Inbox items are never archived and keep their original status (`ACTIONABLE` / `REVIEW_ONLY`) after the work is done. No agent owns archive. Watcher does not watch `inbox/`. Protocol Human role omits deployment; `AGENTS.md` includes it.
- Risk: The human inspect command fails. Codex may see Groq output as `UNKNOWN` if the template is followed literally. Completed Claude Code work remains `ACTIONABLE`, so a second implementer can redo Phase 14. Deployment approval is a missing human-decision boundary in the protocol role list.
- Recommended follow-up: Fix the human inspect command to the real CLI. Add `Status:` to the review template. Require archive or a terminal status on the original request after Codex acceptance. Add deployment to the protocol Human role. Decide whether inbox changes should wake Codex.

## F10 — Severity: MEDIUM

- File: `agent-exchange/status/2026-08-31T145000Z-codex-phase-14-acceptance.md`
- Also: `agent-exchange/inbox/groq/2026-08-31T090000Z-groq-review-phases-8-13-and-exchange.md`, `agent-exchange/status/2026-08-31T090000Z-task-distribution-summary.md`
- Observed issue: Groq’s assigned objective was to review Phases 8–13 and the exchange “before real-data decision intake continues.” Task distribution allowed Claude Code to implement Phase 14 in parallel. Codex already recorded `ACCEPTED_BY_CODEX` for Phase 14 while this Groq review was still pending. Protocol has no gate that Groq review must complete before Codex acceptance. There is no status for “accepted implementation, review found blockers.”
- Risk: Unclear handoff. If this review is blocking, Phase 14 is already accepted with no revision path in the protocol. Humans may start filling decisions against an accepted intake path that this review says is unsafe.
- Recommended follow-up: Codex should reopen Phase 14 as `REVISION_REQUESTED` if it agrees with F1/F2, and add a sequencing rule: Groq review of the previous phase band is required before `ACCEPTED_BY_CODEX` on the next human-facing intake phase.

## F11 — Severity: MEDIUM

- File: `trading_system/data_foundation/storage_policy.py`
- Also: `schemas/raw_data_retention_policy.schema.json`, `configs/data/raw-data-retention-policy.yaml`
- Observed issue: Runtime evaluation hardcodes `retention_approved=False` and copy/upload false, which is good. `MANIFEST_ONLY_ALLOWED` does not fail closed if `approved_storage_roots` is non-empty; it only appends `APPROVED_STORAGE_ROOTS_MUST_BE_EMPTY_UNTIL_APPROVAL`. Schema `maxItems: 0` is not enforced at load time. Policy YAML is a committed file any agent can edit; there is no check that the file hash matches a human decision.
- Risk: A policy edit can look like storage approval. Bundle validation can still return `ACCEPTED_FOR_DRY_RUN` with a non-empty storage-root list sitting in `blocked_reasons`.
- Recommended follow-up: Fail load/evaluate unless storage roots are empty and the policy hash matches the committed manifest-only policy, or require a human decision record to change that file.

## F12 — Severity: MEDIUM

- File: `trading_system/research/offline_dry_run.py`
- Also: `trading_system/candidates/labeling.py`, `tests/research/test_offline_dry_run.py`
- Observed issue: Dry-run tests only the 6-row fixture. Missing edge cases: unsorted rows, duplicate timestamps, DST boundaries, weekend/holiday bars, mixed timeframes, `available_at < observed_at`, naive vs `Z` timestamps in one file, blank numeric fields after the header, more than one canonical symbol after mapping, files large enough to pass `min_train_rows` and emit `TRAINED`, and session-calendar exclusion. Labels walk `future_bars` by `observed_at` with no `available_at` filter (acceptable for outcomes only if features stayed PIT; features currently do). Split bounds are computed from the full file’s timestamps.
- Risk: A real CSV can look like a successful research run while silently dropping INVALID/STALE/CORRECTED bars, training on fixture graph rules, and emitting `TRAINED` without promotion still false being noticed.
- Recommended follow-up: Add adversarial CSV tests listed in Phase 14 recommendations. Keep `promotion_allowed` false, and fail or flag `TRAINED` unless the source is an approved-fixture ID.

## F13 — Severity: LOW

- File: `agent-exchange/protocol.md`
- Also: `agent-exchange/README.md`, `agent-exchange/templates/request.md`
- Observed issue: README says processed items may be moved or copied to `archive/`; protocol says do not mutate inbox files unless asked. No owner, no archive criteria, no mapping from request to result to Codex outcome. Watcher state lives in the system temp directory, so two Codex sessions do not share watch state. Request files are not hashed into results except by a free-text `Request:` field.
- Risk: Lost or double-processed work. Weak audit trail from inbox to acceptance.
- Recommended follow-up: One archive rule, one watch-state location in-repo or per-branch, and a required `Request:` path on every review/status file (this review includes it).

Open questions:

- Codex: are implementation-report Phases 8–14 a side sequence before architecture-plan Phase 4 baselines, or a replacement numbering scheme?
- Codex: may a local-only OHLCV research dataset proceed while order-flow and options remain explicitly deferred, without calling that defer `APPROVED`?
- Human: where will the first real CSV live so it cannot be committed, and who is the named approver for decision records?
- Codex: if Groq blocking findings arrive after `ACCEPTED_BY_CODEX`, is the required status `REVISION_REQUESTED` or a new `REOPENED` value?

Recommended next action:

Codex should record `REVISION_REQUESTED` against Phase 14 / the real-CSV path for F1 and F2, keep human decision collection blocked for production-dataset effects, and only then route a scoped Claude Code contract. Do not treat this review as architecture approval or as a substitute for human decisions under `agent-exchange/decisions/`.

Phase 14 acceptance-test recommendations:

These are test recommendations only. They are not an implementation, not data approval, and not promotion approval.

1. Decision store coupling
   - SATISFIED is rejected unless every evidence path exists under `agent-exchange/decisions/` and contains approver, timestamp, scope, decision, and evidence.
   - A YAML in `configs/` or `/tmp` cannot produce `READY_FOR_PRODUCTION_DATASET`.
   - The committed decisions template still yields `satisfied_count: 0`.
   - Missing, non-existent, or inbox-path evidence fails closed.

2. Defer is not approval
   - Vendor / order-flow / options defer cannot use `APPROVED`.
   - A defer decision cannot satisfy `PRODUCTION_OHLCV_VENDOR_DECISION`.
   - OHLCV-only dataset construction, if Codex later allows it, must remain independently gated from order-flow and options feature builds.

3. Fixture isolation
   - A CSV whose raw symbol is `SPY` plus metadata canonical symbol other than `TR_FIXTURE_SPY` fails until a human-owned symbol-map entry exists.
   - A non-fixture `source_id` must not emit `ohlcv-fixture-v1`, `TR_FIXTURE_SPY`, `fixture-candidate-dataset`, `FIXTURE_NEUTRAL`, or `fixture-graph-rules`.
   - Fixture CSV + fixture metadata remains the only path allowed to use fixture IDs.

4. Point-in-time inspection/onboarding
   - Naive timestamps parse only with the metadata timezone, and that timezone must match the loaded policy or fail.
   - `available_at < observed_at` fails inspection and onboarding.
   - Blank `raw_symbol`, duplicate timestamps, high < low, empty file, and multi-symbol files are `BLOCKED` with explicit reasons.
   - Inspection green is insufficient for bundle acceptance without symbol-map membership.

5. Retention bypass
   - `run_local_csv_dry_run.py` without a passing bundle/retention result fails.
   - Edited retention YAML with non-empty `approved_storage_roots` cannot return `ACCEPTED_FOR_DRY_RUN`.
   - `source_status` other than `OPEN_HUMAN_DECISION` cannot onboard on the local-CSV research path.

6. Output hygiene
   - Tool JSON must not include raw OHLCV rows.
   - Absolute user home paths must not be required in exchange files.
   - A tracked `*.csv` outside `tests/fixtures/` is a test failure or gitignore rule.

7. Exchange workflow
   - Review files without `Status:` are invalid.
   - After `ACCEPTED_BY_CODEX` or `REVISION_REQUESTED`, the original inbox item is no longer `ACTIONABLE`.
   - Watcher `--once` on this review file reports `REVIEW_READY_FOR_CODEX`.
   - Human inspect command in the human inbox matches `inspect_local_ohlcv_csv.py --help`.

8. Ready-status contradiction
   - No payload may set `status=READY_FOR_PRODUCTION_DATASET` while `blocked_actions` contains `BUILD_PRODUCTION_TRAINING_DATASET`.
   - Default `python tools/real_data_readiness.py` remains `BLOCKED`, `satisfied_count=0`, `decisions_version=null`.

Blocking-issue statement:

Blocking issues WERE found (F1, F2). No statement of “no blocking issues” applies. The default tree is still correctly blocked for production dataset construction and production model training, but that default does not make the real-CSV or decision-intake paths safe.

Verification reviewed:

- Branch: `plan/tree-to-trained-model-langgraph` (matches the request).
- `python tools/real_data_readiness.py`: PASS. Status `BLOCKED`, `satisfied_count: 0`, `open_count: 7`, `decisions_version: null`. Blocked actions still include production dataset, production training, claim-edge, promotion, live trading, broker execution, and capital allocation.
- `python tools/inspect_local_ohlcv_csv.py --help`: PASS. Flags are `--csv`, `--source-id`, `--canonical-symbol` (not `--input`).
- `python tools/onboard_ohlcv_csv.py --help`: PASS. Requires `--csv` and `--metadata`.
- `python tools/validate_local_source_bundle.py --help`: PASS. Requires `--csv`, `--metadata`, `--retention-policy`.
- `python tools/run_local_csv_dry_run.py --help`: PASS. Requires `--csv` and `--metadata` only (no retention flag; see F4).
- `python -m pytest tests/data_foundation tests/research -v`: PASS, 82 passed.

Notes:

- No code was edited except this review file.
- No data was approved.
- No model was promoted.
- No architecture decision was made.
- No commit or push was made.
- No secrets, raw market-data payloads, credentials, broker/account data, or private identifiers are included here.

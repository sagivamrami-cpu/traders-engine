# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-08-31T173500Z-groq-review-phase-16-real-source-identity-contracts.md`

Request:
`agent-exchange/inbox/groq/2026-08-31T173500Z-groq-review-phase-16-real-source-identity-contracts.md`

Created at:
2026-08-31T19:10:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
BLOCKING_ISSUES_FOUND

Review-only. This does not approve data, promotion, architecture, live trading,
broker execution, capital allocation, or deployment. Default readiness remains
`BLOCKED`. Phase 16 is already `ACCEPTED_BY_CODEX`; the findings below are
reasons that acceptance should be reopened for the identity-ref contract.

Findings:

## F1 — Severity: BLOCKING

- File: `trading_system/data_foundation/source_identity.py`
- Also: `tests/data_foundation/test_source_identity.py`, `docs/implementation-reports/phase-16-real-source-identity-contracts.md`
- Observed issue: `human_decision_ref` is accepted when the string starts with `agent-exchange/decisions/` and ends with `.md`. The file need not exist, need not be a human decision record, and is not resolved against `..` segments. A relative escape under `decisions/` therefore counts as a valid ref. `validate_source_identity` then returns `REAL_SOURCE_PENDING_HUMAN_DECISION` with `production_allowed=false`.
- Risk: A mere path string is mistaken for a human-decision boundary. Inbox/status files, missing files, and path traversal all get the same pending-real-source status as a real decisions record. Onboarding treats any non-`BLOCKED` identity as passable, so this status is an operational green light, not only a label.
- Concrete failing scenario: Real-source metadata with `source_id=real-ohlcv-spy-1m`, `canonical_symbol=SPY.US`, and `human_decision_ref=agent-exchange/decisions/../inbox/human/<existing-human-inbox>.md` returns `REAL_SOURCE_PENDING_HUMAN_DECISION`. The same status is returned for `agent-exchange/decisions/example.md` when that file does not exist. Verified in this review run.
- Recommended fix: Resolve the ref to a real file under `agent-exchange/decisions/` with no parent-directory escape. Require the markdown to contain Approver, timestamp, Scope, Decision, and Evidence. Missing or traversable refs must be `BLOCKED` with `HUMAN_DECISION_REF_NOT_A_RECORD`.
- Blocks Phase 16 acceptance: YES. The request explicitly asked whether a file reference under `agent-exchange/decisions/` could be mistaken for human approval. The current contract does that.

## F2 — Severity: HIGH

- File: `trading_system/data_foundation/csv_onboarding.py`
- Also: `trading_system/research/source_bundle.py`, `trading_system/research/offline_dry_run.py`
- Observed issue: Onboarding raises only when identity status is `BLOCKED`. `REAL_SOURCE_PENDING_HUMAN_DECISION` continues into manifest emission. Bundle validation does the same, then calls dry-run, which raises `real-source dry-run path is not implemented in Phase 16` instead of returning a schema-valid `BLOCKED` payload. Manifest `raw_file` is still an absolute local path.
- Risk: Pending identity is treated as valid enough to onboard. Bundle/CLI can crash instead of fail closed. Absolute paths can be pasted into `agent-exchange/`.
- Concrete failing scenario: After a symbol-map entry exists for a real canonical symbol, onboard a CSV with a non-existent `human_decision_ref` under `decisions/`. Identity is pending, onboarding emits a manifest, bundle then raises instead of `status=BLOCKED`.
- Recommended fix: Treat `REAL_SOURCE_PENDING_HUMAN_DECISION` as not onboardable and not bundle-acceptable. Catch the dry-run “not implemented” path and return schema-valid `BLOCKED`. Redact local paths in onboard/bundle JSON the same way Phase 17 intends for intake packets.
- Blocks Phase 16 acceptance: YES for the pending-as-passable identity gate. Path redaction can be Phase 17 if onboard/bundle are removed from the human flow; they are still in the human inbox today.

## F3 — Severity: HIGH

- File: `trading_system/features/market_state.py`
- Also: `configs/data/source-identity-policy.yaml`, `trading_system/candidates/generation.py`, `trading_system/datasets/factory.py`
- Observed issue: Identity policy lists fixture graph/dataset IDs (`fixture-candidate-graph-v1`, `fixture-candidate-dataset`) but does not consult them except as optional metadata fields that real-source YAML does not require. The live fixture graph id is `tr-vshape-retest-long` with version `fixture-graph-rules-0.1.0`. Market-state snapshots still hardcode `availability={"ohlcv-fixture-v1": True}` and `regime={"primary": "FIXTURE_NEUTRAL"}`. Session calendar `us-equities-regular-v1` is not in the fixture-only set.
- Risk: The identity contract does not actually fence graph, dataset, regime, availability, or calendar identities. A later real-source dry-run would inherit fixture brain/regime/source keys even if `source_id` looked real.
- Concrete failing scenario: Enable a real-source dry-run while keeping current `build_unified_market_state` and `generate_fixture_candidate`. A non-fixture `source_id` still emits fixture availability, fixture regime, fixture graph, and `fixture-candidate-dataset`.
- Recommended fix: Make fixture graph/dataset/regime/availability/calendar IDs first-class forbidden identifiers for `mode=REAL_SOURCE`, and stop hardcoding fixture availability/regime in market state. Do not invent replacement IDs here; leave them `OPEN_HUMAN_DECISION`.
- Blocks Phase 16 acceptance: NO, as long as real-source dry-run stays unimplemented. YES before any real-source research path is opened.

## F4 — Severity: MEDIUM

- File: `trading_system/data_foundation/source_identity.py`
- Also: `configs/data/source-identity-policy.yaml`, `trading_system/research/readiness.py`
- Observed issue: `allowed_deferred_producers` is loaded and never used. Identity cannot record or reject order-flow/options deferral. Readiness already has a distinct `DEFERRED` value that does not satisfy items; identity does not share that vocabulary.
- Risk: Operators can treat identity pending plus a prose “defer options” note as source approval. The two contracts can drift.
- Concrete failing scenario: Real OHLCV metadata reaches `REAL_SOURCE_PENDING_HUMAN_DECISION` with no order-flow/options decision. Identity payload has no producer-defer field. A later agent copies that pending status into a vendor-approval story.
- Recommended fix: Either drop unused `allowed_deferred_producers` or emit explicit `DEFERRED`/`NOT_DECIDED` producer flags that cannot equal source approval.
- Blocks Phase 16 acceptance: NO.

## F5 — Severity: MEDIUM

- File: `configs/data/local-csv-onboarding-template.yaml`
- Also: `tools/inspect_local_ohlcv_csv.py`
- Observed issue: Fixture metadata still uses `source_status: OPEN_HUMAN_DECISION` while identity mode is `FIXTURE_ONLY`. Inspection CLI still prints `csv_path` as a local filesystem path and still defaults asset class, venue, timeframe, and calendar.
- Risk: Fixture sources look like open human decisions. Humans following the current inbox inspect command can leak absolute paths into exchange files.
- Concrete failing scenario: Run `tools/inspect_local_ohlcv_csv.py --csv <local-file> --source-id ... --canonical-symbol ...` and paste stdout into `agent-exchange/`. The JSON contains the local path.
- Recommended fix: Keep fixture `source_status` distinct from open real-source status. Point humans only at a redacting command (Phase 17 packet), or redact inspect/onboard/bundle outputs.
- Blocks Phase 16 acceptance: NO for identity classification of the committed fixture template. Path leakage is a Phase 17 blocker if inspect remains the human tool.

Open questions:

- Codex: should `REAL_SOURCE_PENDING_HUMAN_DECISION` exist at all before a resolvable decisions-record is present, or should missing records stay `BLOCKED`?
- Codex: is Phase 16 still accepted, or does F1 reopen it as `REVISION_REQUESTED`?

Recommended next action:

Codex should record `REVISION_REQUESTED` on the Phase 16 identity-ref contract (F1, F2) before Phase 17 human intake is accepted. Do not treat `REAL_SOURCE_PENDING_HUMAN_DECISION` as evidence of a human decision. Keep production dataset construction blocked.

Blocking-issue statement:

Blocking issues WERE found (F1, F2). There is no “no issues found” claim for Phase 16.

Verification reviewed:

- `python tools/validate_phase15.py`: PASS (`Phase 15 artifacts validated`).
- `python tools/validate_phase16.py`: PASS (`Phase 16 artifacts validated`). Validators do not cover traversal or missing decision files.
- `python tools/real_data_readiness.py`: PASS. Status `BLOCKED`, `satisfied_count: 0`, report version `real-data-readiness-report-0.3.0`.
- Groq inbox check: Phase 8–13 item is `REVISION_REQUESTED`; Phase 16 and Phase 17 items are `REVIEW_ONLY`.
- Adversarial identity checks in this review: path-traversal ref, missing `decisions/` file, and the Phase 17 UNSET template all returned `REAL_SOURCE_PENDING_HUMAN_DECISION`.

Notes:

- No implementation code was written.
- No data, promotion, or architecture approval is implied.
- No secrets, raw CSV rows, credentials, account identifiers, or absolute user paths are included here.

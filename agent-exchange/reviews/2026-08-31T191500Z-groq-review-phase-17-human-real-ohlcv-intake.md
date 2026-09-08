# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-08-31T183500Z-groq-review-phase-17-human-real-ohlcv-intake.md`

Request:
`agent-exchange/inbox/groq/2026-08-31T183500Z-groq-review-phase-17-human-real-ohlcv-intake.md`

Created at:
2026-08-31T19:15:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
BLOCKING_ISSUES_FOUND

Review-only, including the Phase 17 plan and the partial implementation already
in the tree. No Phase 17 Codex acceptance file exists. This review does not
approve data, promotion, architecture, live trading, broker execution, capital
allocation, or deployment.

Findings:

## F1 — Severity: BLOCKING

- File: `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- Also: `tools/inspect_local_ohlcv_csv.py`, `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- Observed issue: Phase 17 plan Task 3 requires the human inbox to point at `python tools/prepare_real_ohlcv_intake.py --csv ... --metadata ...` and to warn that packet output is not approval. The human inbox still tells humans to run `inspect_local_ohlcv_csv.py`, which prints `csv_path` as a local filesystem path. Inspection JSON is not redacted. Onboard and bundle CLIs also emit absolute paths.
- Risk: The human-facing intake path still leaks absolute local paths into stdout that can be pasted into `agent-exchange/`. That is the exact leakage Phase 17 was created to stop.
- Concrete failing scenario: A human follows the current inbox verification command, inspects a real CSV, and pastes the JSON into a decision or status file. The payload contains the local path. `prepare_real_ohlcv_intake.py` exists but is not the documented human command.
- Recommended fix: Update the human inbox only after the redacting CLI is the unique documented intake command. Stop documenting inspect/onboard/bundle as human paste-into-exchange tools, or redact those CLIs too.
- Blocks Phase 17 acceptance: YES.

## F2 — Severity: BLOCKING

- File: `configs/data/real-ohlcv-source-metadata-template.yaml`
- Also: `trading_system/data_foundation/source_identity.py`
- Observed issue: The template’s `human_decision_ref` is `agent-exchange/decisions/UNSET_HUMAN_DECISION_RECORD.md`. That string passes the Phase 16 prefix/suffix check. Validating the template yields `REAL_SOURCE_PENDING_HUMAN_DECISION`, not `BLOCKED`. Sentinel `UNSET_*` field values are otherwise treated as complete metadata.
- Risk: Copying the “blocked” template produces pending-real-source identity without a human decision record. A later agent can treat the template as already in the pending-approval lane.
- Concrete failing scenario: `validate_source_identity` on the committed real-source template returns `REAL_SOURCE_PENDING_HUMAN_DECISION` with only `PRODUCTION_APPROVAL_REQUIRED`. Verified in this review run.
- Recommended fix: Sentinels must fail identity (`UNSET_` prefix blocked, or ref must resolve to an existing decisions record). Keep `human_decision_ref` a non-decisions placeholder that the current matcher rejects, or reject UNSET refs explicitly.
- Blocks Phase 17 acceptance: YES.

## F3 — Severity: HIGH

- File: `trading_system/research/intake_packet.py`
- Also: `schemas/real_ohlcv_intake_packet.schema.json`, `tests/research/test_intake_packet.py`
- Observed issue: Packet tests build a “real OHLCV intake packet” from fixture metadata (`local-csv-onboarding-template.yaml`) plus a shape-fixed fixture CSV. A valid-shape fixture run returns `status=BLOCKED_NEEDS_HUMAN_DECISION` with nested `source_identity.status=FIXTURE_ONLY` inside `mode=REAL_OHLCV_INTAKE_PACKET`. Nested `inspection` allows `additionalProperties`. Hash, symbols, and date range of fixture data are therefore a documented intake packet.
- Risk: Fixture hash/symbols can be copied as evidence of a real CSV. A fixture packet looks like the human intake success path. Extra inspection fields added later can leak paths because the nested schema is open.
- Concrete failing scenario: Run the packet builder on the committed fixture CSV after fixing the invalid OHLC row used in tests. Packet status is `BLOCKED_NEEDS_HUMAN_DECISION`, not `BLOCKED_INVALID_INPUT` for fixture identity. A human or agent pastes `raw_file_sha256` into a decisions evidence list.
- Recommended fix: Fixture identity must force `BLOCKED_INVALID_INPUT` (or a fixture-only status that is not the human-intake success status). Close nested inspection properties. Reject fixture hashes as readiness evidence (Phase 15 already tries this on the decisions side; the packet should not emit a human-looking success for fixture mode).
- Blocks Phase 17 acceptance: YES if the packet is the human evidence artifact. NO if Codex forbids fixture packets as evidence by a separate gate before any decision file is written.

## F4 — Severity: HIGH

- File: `tools/prepare_real_ohlcv_intake.py`
- Also: `tools/onboard_ohlcv_csv.py`, `tools/validate_local_source_bundle.py`, `tools/run_local_csv_dry_run.py`
- Observed issue: The redacting CLI still takes `--csv` as a real local path. Argparse errors print that path (the plan allows this). Onboard, bundle, and dry-run remain available and print unredacted `csv_path` / `raw_file`. Packet builder does not run retention or readiness gates; it only inspects and validates identity.
- Risk: Humans can bypass the packet CLI and use older tools. Packet `BLOCKED_NEEDS_HUMAN_DECISION` can be read as “ready for decisions” even when readiness, retention, and real symbol-map entries are missing.
- Concrete failing scenario: Human runs onboard or inspect instead of the packet CLI and pastes absolute paths. Or human treats packet status `BLOCKED_NEEDS_HUMAN_DECISION` as permission to write an `APPROVED` decision using the packet hash alone.
- Recommended fix: Keep packet status from implying decision-readiness beyond “shape/identity report.” Document older CLIs as non-exchange tools. Do not let packet output satisfy any checklist item.
- Blocks Phase 17 acceptance: YES for documenting a single non-leaking human command. NO for keeping packet `production_allowed=false` (that part is correct).

## F5 — Severity: MEDIUM

- File: `trading_system/research/intake_packet.py`
- Also: `agent-exchange/templates/human-decision-record.md`, `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- Observed issue: Packet always lists order-flow and options among `required_decision_records` with no `DEFERRED` token. The human decision template has a free-text `Decision:` field and does not constrain values to `APPROVED` / `NOT_APPROVED` / `DEFERRED`. Plan Task 3 (validator, implementation report, human inbox update) is not in the tree: no `tools/validate_phase17.py`, no `tests/research/test_phase17_validator.py`, no Phase 17 implementation report, no Codex status result.
- Risk: Incomplete Phase 17 can be mistaken for done because packet module, schema, CLI, and unit tests exist. Free-text Decision fields can encode defer as approval. Required-record lists can pressure fake `APPROVED` defers.
- Concrete failing scenario: Claude Code or Codex treats current files as Phase 17 complete. Human fills `Decision: deferred, treat as approved for OHLCV` in the template and a later YAML maps it to `APPROVED`.
- Recommended fix: Finish plan Task 3. Constrain the decision template enum. Packet should list order-flow/options as optional defer-capable items, not as the same class as vendor approval.
- Blocks Phase 17 acceptance: YES until Task 3 artifacts exist. The current tree is not an acceptable Phase 17 completion.

## F6 — Severity: MEDIUM

- File: `docs/superpowers/plans/2026-08-31-phase-17-human-real-ohlcv-intake-packet.md`
- Also: `agent-exchange/protocol.md`
- Observed issue: Plan says a local CSV path may be supplied to the CLI but must never appear in committed files or agent-exchange outputs. Protocol still forbids raw payloads in exchange files, which is good, but does not forbid inspect/onboard JSON. Plan tests forbid `C:\\` and `/Users/` in packet JSON; they do not forbid repo-relative fixture paths in all tools, and they use the fixture file as the happy-path input.
- Risk: Leak checks are string-subset tests. A path without those prefixes (for example a relative path or another drive convention) can pass. Fixture-as-happy-path trains the wrong evidence shape.
- Concrete failing scenario: Packet JSON includes a relative `csv_path` other than `LOCAL_PATH_REDACTED` that does not contain `C:\\` or `/Users/` — current tests would not catch it if redaction regressed to a relative path. The schema const on `csv_path` would catch that; inspect CLI has no such const.
- Recommended fix: Keep schema const `LOCAL_PATH_REDACTED` on every human-facing JSON. Add tests that inspect/onboard/bundle are either unused or equally redacted. Do not use fixture CSV as the documented human success path.
- Blocks Phase 17 acceptance: NO for the packet schema const itself (that part is sound). YES if inspect remains human-facing without the same const.

Open questions:

- Codex: should Phase 17 implementation continue from the partial tree, or be reset to tests-first against a hardened identity-ref contract from the Phase 16 review?
- Human: the only safe place for a real CSV path is local CLI argv, never an exchange file. Is that acceptable, or is even argv-in-shell-history a problem for this desk?

Recommended next action:

Do not accept Phase 17. Keep human decision collection blocked. Route Phase 16 F1/F2 identity-ref hardening first, then finish Phase 17 Task 3 with: UNSET refs blocked, human inbox pointed only at the redacting CLI, fixture packets not using the human success status, and a Phase 17 validator/report.

Blocking-issue statement:

Blocking issues WERE found (F1, F2, F5, and F3/F4 as acceptance blockers for the human evidence path). There is no “no issues found” claim for Phase 17.

Verification reviewed:

- `python tools/validate_phase16.py`: PASS (`Phase 16 artifacts validated`).
- `python tools/real_data_readiness.py`: PASS. Status `BLOCKED`, `satisfied_count: 0`.
- Groq inbox check: this Phase 17 item is `REVIEW_ONLY`; no Phase 17 implementation status file exists.
- `tools/validate_phase17.py`: NOT PRESENT.
- Identity of the committed real-source metadata template: `REAL_SOURCE_PENDING_HUMAN_DECISION` (see Phase 16 review F1 and this review F2).

Notes:

- No implementation code was written.
- No data, promotion, or architecture approval is implied.
- No secrets, raw CSV rows, credentials, account identifiers, or absolute user paths are included here.

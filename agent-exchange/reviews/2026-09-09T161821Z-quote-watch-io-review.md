# Agent Exchange Review

Reviewer: Codex independent task reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T161821Z-quote-watch-io-review.md
Request: agent-exchange/inbox/codex/2026-09-09T161821Z-quote-watch-io-review.md

Created at: 2026-09-09T16:20:57Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec PASS. Code quality PASS. Ready for independent final component review; no revision required from this task review.

## Review basis

Read AGENTS.md, exchange README/protocol, inspected the Codex inbox, and read the exact request. Applied requesting-code-review/SKILL.md and its code-reviewer.md guidance directly, without nested agents. Read the named causal-quote-watch-io plan, CAUSAL-QUOTE-WATCH-IO-CONTRACT.md, this task's scratch progress/report/package, and the implementation exchange report. Inspected git status and tracked diff; unrelated dirty work was preserved.

Base and current HEAD: c1b6071633c55376c64f0a98ece843706f420f49. Reviewed all eight actual additions, not an empty HEAD..HEAD diff. Independently reconstructed the added lines from task-1-diff.md and compared them with all eight working files: all match, including line counts.

Files reviewed completely:

- trading_system/tree_replay/admission_io.py
- trading_system/tree_replay/_vendor/watch_io.py
- trading_system/tree_replay/_vendor/watch_sessions.py
- trading_system/tree_spec/watch_io_source.py
- tools/check_watch_io_source_parity.py
- tests/tree_replay/test_admission_io.py
- tests/tree_spec/test_watch_io_source.py
- docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md

Retained source parent fixed for this review:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Expected chart-desk commit: `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
Read original complete `_log`, `session_mask`, `current_session`, and inherited SessionSpec/SESSIONS/_hm/psy_levels; inspected accepted UTC/identity/audit helpers and tracker quote, born-state and rejection/tail consumers for integration risks. No retained source was executed and no next-source lifecycle/lock intake was performed.

## Strengths and spec assessment

- `admission_io.py:30`: seed validation preserves exact content types, trimmed UTF-8 identities, microsecond-exact UTC and ordered publication/coverage. Known absence, unreadable evidence, unknown evidence, malformed JSON and valid nonobject JSON retain distinct boundaries. Fresh parsing detaches quote payloads; original tracker owns price validation and freshness.
- `_vendor/watch_io.py:8`: the full logger preserves eager session calculation, caller mutation before mkdir/open, open-before-serialization creation, clock evaluation despite caller ts override, insertion order and original JSON options. Append encoding completes before chunks change; parent and child failure traces remain visible.
- `admission_io.py:110`: captured byte length and bounded reads prevent later chunks leaking through old readers, including after advance. Bisection handles exact chunk boundaries; seek/tell/read supply the operations used by the original widening tail reader. Existing malformed/non-rejection bytes and torn final lines remain untouched. Snapshot alone explicitly exports the full prefix; normal opens do not join it.
- `admission_io.py:223`: advance validates the proposed clock before mutation, preserves append storage, and retains failure evidence. Snapshot publication is the current decision time, independently of a caller-overridden payload ts. Coverage remains an explicit caller attestation.
- `watch_io_source.py:21`: exact AST substitutions retain logger order and specialize only the session clock/signature. Whole-module checks include imports and the complete inherited four-symbol projection; annotated SESSIONS selection is explicit. Commit, baseline and source blob mismatches remain blockers. CLI success/failure and false readiness are consistent with the contract.
- Tests exercise actual accepted quote/born and rejection consumers, literal LF/CRLF output, session clocks, caught failures, delayed/expired evidence, immutable reader cutoffs, chunk crossings, tail widening/read-all and same-pass rejection ties. The new born-state cases exercise `_born_in_zone`; existing tracker tests separately cover its OPEN/PENDING record mapping. This is component evidence, not combined main-loop execution.

## Findings

Critical: none.

Important: none.

Minor: none requiring action in this scoped package.

No concrete uncovered runtime risk remained after source and consumer inspection, so no focused probe or suite rerun was justified under the request.

## Verification reviewed

Independent read-only checks: git status/diff inspected; `git rev-parse HEAD` matched the request; PowerShell package-to-file comparison passed for all eight additions; `Get-FileHash -Algorithm SHA256` matched the report's runtime and auditor identities:

- Runtime: `e3efe004e031c3c1831373b7e946b4ff512aad229306ccf3c18999fa0dd38f12`.
- Auditor: `0ff0ed97661a3815598527f09ff807b35381930be35ce4450669b6ea38334dce`.

The following are implementer-reported results reviewed against the test/audit code, not independently rerun results:

```text
python -m pytest tests/tree_replay/test_admission_io.py tests/tree_spec/test_watch_io_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_frames.py -q --tb=short
PASS: 269 tests, including 60 runtime and 13 audit cases.

python tools/check_watch_io_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
PASS: VERIFIED, four projections, no blockers, readiness false.

python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
PASS: VERIFIED, seven projections, no blockers, readiness false.
```

Open questions: none blocking this component. Source-root provisioning and timezone-database lineage remain environmental requirements already documented; they do not certify historical inputs.

Recommended next action: proceed to the required independent final review and controller acceptance. Full caller/lock ordering, watch state and generated lifecycle remain separate work owned by main. This verdict makes no OS concurrency, full-checkpoint, full-loop, economic-label or model-readiness claim.

Only this requested report was written, via apply_patch. No implementation, inbox, other plan scratch, commit or live-system changes.

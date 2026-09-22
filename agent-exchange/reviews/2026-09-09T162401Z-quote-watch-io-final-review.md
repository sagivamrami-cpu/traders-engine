# Agent Exchange Review

Reviewer: Codex independent final component reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T162401Z-quote-watch-io-final-review.md
Request: agent-exchange/inbox/codex/2026-09-09T162401Z-quote-watch-io-final-review.md

Created at: 2026-09-09T16:26:13Z

Status: REVIEW_READY_FOR_CODEX

Verdict: PASS. Ready for controller acceptance of the scoped causal quote/watch IO component. No revisions required by this review.

## Review basis

Read startup AGENTS.md and exchange README/protocol, inspected the Codex inbox, and executed only the assigned final-review request. Applied requesting-code-review and its code-reviewer instructions directly, plus verification-before-completion. No nested agents.

Read the complete causal-quote-watch-io plan, contract, usage, task report/progress, original task-review request, task review161821Z and controller task acceptance162401Z. Inspected current status/diff and actual additions at HEAD `c1b6071633c55376c64f0a98ece843706f420f49`; an empty HEAD..HEAD comparison was not used as implementation evidence.

Reviewed all eight additions completely:

- `trading_system/tree_replay/admission_io.py`
- `trading_system/tree_replay/_vendor/watch_io.py`
- `trading_system/tree_replay/_vendor/watch_sessions.py`
- `trading_system/tree_spec/watch_io_source.py`
- `tools/check_watch_io_source_parity.py`
- `tests/tree_replay/test_admission_io.py`
- `tests/tree_spec/test_watch_io_source.py`
- `docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md`

Independently reconstructed every added line from the full task-1-diff.md package and compared against the eight actual files: all matched. Runtime and auditor SHA256 also match the implementation report:

- Runtime: `e3efe004e031c3c1831373b7e946b4ff512aad229306ccf3c18999fa0dd38f12`.
- Auditor: `0ff0ed97661a3815598527f09ff807b35381930be35ce4450669b6ea38334dce`.

Read retained original `_log`, `session_mask`, `current_session`, and the four inherited session symbols. Inspected accepted UTC/identity/audit helpers and tracker quote, born-state, raw-tail and rejection consumers. Source parent: `C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`; chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`. Retained source was parsed/read, never executed. No next lock/caller/lifecycle intake was performed.

## Strengths and combined assessment

- `admission_io.py:30`: exact frozen seed types, UTF-8 identities and microsecond UTC ordering preserve the evidence contract. Quote publication/coverage gates precede parsing; fresh parses detach payloads. Missing, unreadable, unknown, malformed and nonobject inputs retain their specified source boundaries. Tracker freshness and symbol behavior remain unchanged.
- `_vendor/watch_io.py:9`: eager session calculation and caller mutation precede directory/open operations. Append opening precedes serialization, caller ts/sessions and insertion order survive, and the clock still runs when ts is overridden. Failed serialization retains absent-file creation; encoding completes before any byte append. Parent failure traces remain visible after consumer catches.
- `admission_io.py:110`: captured length clips old readers despite shared append-only chunk arrays. Bisection and span slicing preserve exact malformed/non-rejection prefixes and source tail widening without copying the full log on open. Explicit snapshot export and monotonic covered advance remain separate operations.
- `watch_io_source.py:21`: exact substitutions and whole-module AST comparisons preserve logger/session behavior, including imports and the inherited annotated session table. Commit, baseline, blob and projection mismatches block verification. No runtime audit or historical-data certification is implied.
- Tests cover actual quote/born and rejection consumers, literal newline profiles, sessions, failure ordering, source catches, delayed/expired evidence, captured readers and same-pass appends. New quote integration exercises `_born_in_zone`; existing tracker tests separately verify OPEN/PENDING recording. These compositional checks do not establish a combined market-watch loop.

## Findings

Critical: none.

Important: none.

Minor: none requiring action in this scoped component.

## Verification reviewed

Independently executed:

1. `git rev-parse HEAD`, `git status --short`, scoped `git diff`, package-to-file PowerShell comparison and `Get-FileHash -Algorithm SHA256`: inspected actual additions; all eight package contents and both reported hashes matched. Tracked whitespace check produced no defects, only LF/CRLF warnings; it does not validate untracked additions.
2. `python -B tools/check_watch_io_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`: exit0, VERIFIED, four projections, no blockers, replay/training readiness false.
3. `python -B -` with an in-memory deterministic differential probe: exit0, 4,936 reader/tail comparisons passed. The probe used Random(162401), both LF/CRLF profiles, empty and invalid-UTF8/torn seeds, 40 appends with clock advances, and readers captured before every later append. It compared seek/read/tell against BytesIO snapshots for 30 mixed-origin reads per captured reader, plus original tail-reader results for window/cap pairs (1,1), (8,64), (16,1024), (400000,8000000). This specifically checked multi-chunk boundary and old-reader isolation concerns; no probe file was written.

Reviewed controller/implementer evidence, not rerun by this final reviewer:

```text
python -m pytest tests/tree_replay/test_admission_io.py tests/tree_spec/test_watch_io_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_frames.py -q --tb=short
Controller-reported PASS: 269 tests in 16.30s, exit0.

python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
Implementation-reported PASS: seven projections, no blockers, readiness false.
```

Original RED/GREEN chronology is implementation-reported evidence; I did not recreate it. No large suite rerun was needed after the focused probe resolved the remaining reader concern.

Open questions: none blocking component acceptance. Explicit source provisioning, timezone lineage and historical publication/coverage attestations remain documented limitations.

Recommended next action: controller may accept this component and continue its separately owned source lock/caller/lifecycle work. This verdict does not certify OS concurrency, a complete checkpoint or replay, economic labels, datasets or models.

Only this requested report was written, via apply_patch. No implementation, inbox, other scratch, branch, commit or live-system changes.

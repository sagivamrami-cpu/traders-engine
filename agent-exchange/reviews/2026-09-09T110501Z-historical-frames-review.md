# Agent Exchange Review

Reviewer:
Codex independent Task2 reviewer; no subagents.

Target request:
agent-exchange/inbox/codex/2026-09-09T110501Z-historical-frames-review.md

Created at:
2026-09-09T11:08:04Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec: FAIL — the extracted brief's explicit regression-test deliverable is incomplete. No confirmed runtime correctness defect found in the reviewed implementation.
- Quality: Needs fixes — complete the required boundary coverage and remove the misleading upsampling test before task acceptance.

Findings:

1. **P2 / Medium — Required boundary regressions are missing.** Locations: `tests/tree_replay/test_frames.py:149`, `tests/tree_replay/test_frames.py:187`, `tests/tree_replay/test_frames.py:253`.
   The brief explicitly requires labels crossing UTC day/month boundaries, full coverage checks, and 5m-to-15m/1h/4h forming/final rows. The label test only moves January 1–3 midnight labels to 21:00 on those same dates. The 1h/4h cases stop after 35 minutes and only assert a FORMING row; the separate 4h-origin test also stays inside its first bucket. The metadata test changes publication times, but no test in the complete new test-file diff exercises `CALENDAR_COVERAGE` at the frame boundary. These are distinct from the existing period/selector tests: the wrapper selects periods, checks global coverage and groups target rows itself. Add literal cross-day/month source-label assertions with observation/publication unchanged; valid schedules that start too late or end before the decision, including a missing coverage span between daily periods; and exact 1h/4h closes followed by a forming next bucket, asserting OHLC, state and actual observation time. Expected blocked frames must retain empty rows and null observation/publication fields. This finding concerns missing specified evidence, not a demonstrated price leak.

2. **P3 / Low — The upsampling regression never reaches the upsampling check.** Location: `tests/tree_replay/test_frames.py:309`; relevant implementation: `trading_system/tree_replay/frames.py:68` and `trading_system/tree_replay/frames.py:98`.
   The test changes `base_timeframe` to `30m` while retaining the fixture's `5m` bars. Construction therefore raises the earlier bar/timeframe identity error. Its broad `pytest.raises(ValueError)` would still pass if the target-versus-base duration guard were removed. Use a consistent coarse-base fixture (or an empty bar tuple for this construction-only check), keep target/history/anchor otherwise valid, and assert the upsampling-specific rejection.

Open questions:

**Cannot verify items:**

- Reported RED history, intermediate failures and final suite results were not independently executed or witnessed. The report is evidence of the controller's claims, not independent test certification.
- The absent boundary regressions above cannot be credited as tested behavior. Static inspection found the expected coverage guard, separate source-label field and target-bucket state calculation, but does not replace the explicitly requested tests.
- Historical calendar/feed/source-label provenance, source fidelity beyond this frame contract, full map integration, producer admission and replay/training readiness are outside this review. Caller attestations remain attestations; no GC/OANDA mapping or source execution was used.

Recommended next action:

Controller should complete the narrowly scoped Task2 tests above and obtain review of that delta before recording task acceptance. Full map integration remains controller-owned. No production-code change is requested on the basis of an unconfirmed defect.

The implementation otherwise shows the specified frozen contracts, exact instrument checks, explicit grids and period ordering, causal closed/published base selection, active-period ownership checks, current-period enforcement, closure skipping, missing-history blocking, explicit freshness, missing-volume/overflow handling and false readiness flags. Daily base bars are partitioned before per-period aggregation. Selected daily evidence contributes through aggregate hashes; the supplied calendar remains provenance, so calendar revisions need not be extension-invariant. These observations are independent static findings, not acceptance inferred from the parent implementation or passing tests.

Verification reviewed:

- **PASS, read-only scope check:** read `AGENTS.md`, exchange README/protocol, inspected Codex and human inbox directories, then read the specified request, extracted brief, report, entire new-file diff and review template. Broader implementation/source crawling was not performed.
- **PASS, artifact identity:** `git hash-object trading_system/tree_replay/frames.py tests/tree_replay/test_frames.py docs/architecture/HISTORICAL-FRAMES-USAGE.md` returned `97c741b9d5d200bcf201d06d31ff6b35b069e5a2`, `d81ebff59dde6cfdd3056f2f50c8c47f8533ac9a`, and `aaed9b9aa44f7453b29f8a13f73af8ecbb76907d`, matching the supplied diff's blob prefixes. `git status --short` showed a pre-existing dirty/untracked workspace. Scoped `git diff -- trading_system/tree_replay/frames.py tests/tree_replay/test_frames.py docs/architecture/HISTORICAL-FRAMES-USAGE.md` was empty because these additions are untracked; the full supplied new-file diff was the review basis.
- **PASS, static boundary inspection:** unchanged `periods.py`, `bars.py`, `calendar.py` and `session_bars.py` were inspected to resolve daily completeness/publication/hash propagation, constructor validation, calendar coverage/interval semantics and selector grid/freshness behavior. No baseline acceptance was inferred.
- **Reported PASS; NOT RERUN:** `python -m pytest tests/tree_replay/test_frames.py -q --tb=short` — controller reports 59 passed in 0.71s, exit 0.
- **Reported PASS; NOT RERUN:** `python -m pytest tests/tree_replay/test_periods.py tests/tree_replay/test_session_bars.py -q --tb=short` — controller reports 69 passed in 0.77s, exit 0.
- No routine suites or focused runtime experiments were run: the findings are directly established by the diff and constructor control flow. No source execution, commits, worktrees, cleanup or production edits. This review file is the only reviewer write.

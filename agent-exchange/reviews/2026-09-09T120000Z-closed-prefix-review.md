Spec compliance: PASS for the supplied Task 1 delta.
Task quality: Approved. No Critical, Important, or Minor defects identified.

# Agent Exchange Review

Reviewer: Codex task reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T120000Z-closed-prefix-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec compliant; task quality approved, with the verification limits below. This is a Task 1 review, not controller acceptance or whole-branch approval.

Scope and evidence:

- Brief: `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-1-brief.md`, including its verbatim Global Constraints.
- Report: `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-1-report.md`.
- Diff: `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-1-review-package.diff`. Base/head both `c1b6071633c55376c64f0a98ece843706f420f49`; the reviewed change is the packaged uncommitted delta against saved beforeimages, not an empty commit range.
- Followed the specified `subagent-driven-development/task-reviewer-prompt.md`. All five assigned files have corresponding changes. No original test file is changed in this package.

Strengths and spec checks:

- `trading_system/tree_replay/periods.py:52`: the new keyword-only policy rejects non-bools. Prefix mode floors `min(T, period.closed_at)` using integer UTC-epoch arithmetic while retaining aligned period boundaries. At `periods.py:91`, bar publication is still compared with actual decision time; metadata availability and expected-history checks remain distinct at `periods.py:105`.
- `trading_system/tree_replay/periods.py:136`: prefix calculation/schema versions and observation-cutoff evidence are conditional. The default evidence layout is preserved. `periods.py:163` retains actual observation and publication times, including late publication after period completion.
- `trading_system/tree_replay/frames.py:110`: daily ownership uses actual decision time, and a missing or empty current period cannot silently reuse yesterday's row. `frames.py:169` limits intraday fragment checks to the derived cutoff while forwarding actual decision time to the existing selector.
- `trading_system/tree_replay/frames.py:223`: frame metadata, calendar coverage and exact freshness remain evaluated at actual T; only prefix mode relaxes decision-grid validation. Prefix versions and cutoff enter canonical result/hash evidence. FrameSpec and MapFrameRequest constructor definitions are unchanged in the delta.
- `trading_system/tree_replay/levelmap.py:68`: the optional final `_OfflineSource` argument preserves three-argument construction and forwards the policy to frame construction. `levelmap.py:146` versions map output independently, preserves actual source decision time and false readiness/tradeable flags, and propagates the selected version to the generated snapshot at `levelmap.py:199`. Available frame traces carry the prefix cutoff.
- `tests/tree_replay/test_closed_prefix.py:1`: the added tests exercise public period/frame/map behavior with literal OHLC expectations, delayed publication and unavailable-price invariance, strict/default equality, fixed golden hashes, policy and timestamp validation, freshness boundaries, metadata, calendar coverage, forming higher frames, supplied 23/25-hour periods, rollover, missing versus closed history, and actual-clock source-session changes. Assertions inspect actual map output and dependency traces.
- `docs/architecture/CLOSED-BASE-PREFIX-USAGE.md:18`: documentation distinguishes actual decision time from price observation, states default compatibility and prefix versions, and explicitly preserves unsupported partial/open-only observations and false readiness.

Findings:

- Critical: None.
- Important: None.
- Minor: None.

Focused checks and review limits:

- Named concrete risk: passing arbitrary off-grid T into the existing intraday selector could demand a partial bar or measure age against the floor. Checked `trading_system/tree_replay/session_bars.py:22`: actual T is forwarded; the expected-bar loop at line 75 requires only whole elapsed base bars, missing history blocks at line 93, and freshness uses actual T at line 97. No issue identified.
- The supplied runtime hunks cut off relevant functions. Read only the missing eligibility/aggregation sections of `periods.py:82` and `periods.py:159`, and the daily ownership/bucketing and intraday grouping sections of `frames.py:110` and `frames.py:181`, to complete those checks.
- Read the supplied diff in one review pass. Tool-output truncation hid part of the map/test diff; recovered that omitted span rather than generating another diff or reviewing the branch. No git commands, agents, implementation edits, cleanup, commits or pushes were performed.

Open questions / cannot verify:

- Historical capture of the three pre-change golden hashes and RED-before-implementation chronology cannot be independently established from this delta. The report records them, and the new tests contain the fixed hashes; the controller should retain the original capture/run evidence. This is an evidence limit, not a claim that the evidence is absent.
- Preservation of every unchanged validation path, the independent pinned-source audit, and full producer/B-I behavior cannot be certified by this five-file task package. Existing-suite results are reported below; broader source/pipeline acceptance remains with the controller and subsequent tasks.

Verification reviewed:

- Reported RED: `python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=no -rN` — exit 1, 55 failed, 1 passed, 0.73s. Reported first GREEN: 56 passed, 1.16s. The report explicitly distinguishes six subsequently added characterization cases from the initial TDD run.
- Reported PASS: `python -m pytest tests/tree_replay/test_closed_prefix.py tests/tree_replay/test_periods.py tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap.py -q --tb=short` — exit 0, 213 passed, 6.54s, no pytest warnings.
- Reported PASS: `python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=short` — exit 0, 62 passed, 1.12s, no pytest warnings.
- These are implementer-reported runs, not independently rerun results. No unresolved code-reading doubt required a targeted test. The package contains disclosed LF/CRLF git warnings; these are packaging diagnostics, not test/runtime warnings.
- Startup documents, own Codex inbox listing, assigned request, brief, report, review template and task-reviewer instructions were read. The only write is this assigned review report, using apply_patch.

Recommended next action: Controller may accept Task 1 after reconciling the noted evidence limits. Task 2, Task 3, whole-branch readiness and production approval remain outside this verdict.

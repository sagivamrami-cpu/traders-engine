## Spec Compliance

- Issues found: out-of-session exclusion is preempted by the grid check in `trading_system/tree_replay/periods.py:80`. See Important finding I1.
- Scope: Task 2 and Global Constraints only, reviewed from `task-2-review.diff`; supplied base/head both `c1b6071633c55376c64f0a98ece843706f420f49`, with three new files. No requirements imported from Tasks 1/3 or earlier plans.
- Cannot verify from this diff: whole-branch preservation of pinned chart-desk semantics or completion of the source-tree-to-outcome model. These remain controller/integration responsibilities; this dependency does not replace or complete that objective. The usage document explicitly preserves downstream work at `docs/architecture/DAILY-PERIOD-ASOF-USAGE.md:67`.

## Strengths

- `trading_system/tree_replay/periods.py:20`: frozen period evidence reuses identity and exact timestamp validation, enforces positive duration, and imposes no 24-hour assumption.
- `trading_system/tree_replay/periods.py:64`: price cutoff is capped at period end while publication eligibility uses decision time, allowing genuinely late final publication without applying a historical freshness limit.
- `trading_system/tree_replay/periods.py:91`: coverage validation and clipped session endpoint checks fail closed; expected opens drive first-bar and interior-gap blockers before OHLCV is produced.
- `trading_system/tree_replay/periods.py:115`: hashing binds selected evidence and dependency metadata; result construction retains null blocked observations and false readiness flags. Missing volume stays unknown and finite summation rejects overflow.
- `tests/tree_replay/test_periods.py:44`: literal OHLCV expectations exercise real aggregation; subsequent cases cover late publication, gaps, closures, fragments, volume, suffix invariance, metadata, invalid inputs and 23/25-hour periods.
- `docs/architecture/DAILY-PERIOD-ASOF-USAGE.md:34`: documentation clearly limits forming observations to lower-bar closes and disclaims open-only observations, inferred periods and complete historical maps.

## Issues

### Critical

- None found.

### Important

- **I1 — Exclude closure-only bars before enforcing aggregation-grid alignment.** `trading_system/tree_replay/periods.py:80` raises on every temporally eligible off-grid bar before consulting session intervals. A valid inherited `ClosedBar` need only have the exact timeframe duration; its open need not lie on the epoch grid (`trading_system/tree_replay/bars.py:80`). For a 00:00–00:20 period with open sessions 00:00–00:05 and 00:15–00:20, the two scheduled bars yield CLOSED. Adding a published 00:06–00:11 five-minute bar entirely inside the declared closure instead raises `ValueError: selected bar opens must align to base grid`. Task 2 requires out-of-session selected bars to be excluded and counted, so this unrelated observation incorrectly prevents a complete day's output. Determine session membership before applying the grid restriction to contributing bars; preserve validation of every input's identity/type/duplicates and the existing session-fragment blockers. Add a regression asserting unchanged OHLCV, CLOSED status and excluded count 1 for this case.

### Minor

- None requiring separate action.

## Checks and Evidence

- Read `AGENTS.md`, exchange README/protocol and the specified `task-reviewer-prompt.md`; inspected Codex inbox filenames. Followed the user's restricted review scope and single-output-path instruction.
- Read the supplied diff once, including all three complete added files; no changed-file rereads, git commands, nested agents or suite reruns.
- Named inherited-bar risk: aggregation assumes valid duration, publication ordering, finite OHLCV and exact timestamps for every `ClosedBar`. Focused inspection of `trading_system/tree_replay/bars.py:23`, `:35`, `:52` and `:80` confirms constructor validation and shows grid alignment is not part of that inherited contract.
- Named inherited-calendar risk: expected-open iteration assumes chronological, disjoint intervals to avoid double-counted volume and incorrect first/last prices. Focused inspection of `trading_system/tree_replay/calendar.py:31` and `:51` confirms exact timestamps, positive intervals, coverage containment, sorting, overlap rejection and adjacent-interval merging.
- Implementer evidence: `task-2-report.md:12` reports 38 RED failures for the missing module followed by 38 GREEN passes in 1.60s, exit 0, using `python -m pytest tests/tree_replay/test_periods.py -q --tb=short`. No test warnings are reported; CRLF notices in the diff package are packaging output, not test failures. These runs were not repeated.
- Focused synthetic probe, executed through PowerShell here-string input to `python -B -`: scheduled bars only -> `CLOSED`; adding the closure-only bar -> `ValueError selected bar opens must align to base grid`. Probe exit 0. An initial inline invocation failed at Python parsing because PowerShell stripped quotes; the corrected stdin invocation above established I1 without creating a script file.
- No raw feeds, live effects, commits, worktrees or implementation edits. Only this requested review artifact was written with `apply_patch`.

## Assessment

- **Task quality: Needs fixes.** One reproducible session-exclusion defect violates the task's explicit contract. The remaining reviewed implementation is compact, causal and supported by meaningful synthetic tests; acceptance should follow correction of I1 and its focused regression.

# Task 1 implementation report

Target: Codex parent/controller

Sender: Codex schedule-sidecar implementer

Created at: 2026-09-09T08:43:46Z

Request: `.superpowers/sdd/2026-09-09-session-ema-history/task-1-brief.md`

Status: DONE / IMPLEMENTED_AWAITING_CODEX_REVIEW

Commits created: none.

## Implemented

- Added frozen, keyword-only `SessionInterval` and `SessionSchedule` contracts with every specified field required.
- Reused `bars._utc` and `bars._validate_identity(instrument, "5m")`. Aware timestamps normalize to native UTC without rounding; naive and submicrosecond inputs fail. Schedule publication has no artificial ordering relation to coverage.
- Explicit half-open coverage and intervals; empty tuple declares fully closed coverage. Validated tuple contents and bounds, rejected overlaps/duplicates, sorted intervals and merged only exactly adjacent intervals without mutating inputs. Microsecond gaps remain gaps.
- Added `schedule_from_research_calendar` using the existing `data_foundation.sessions.resolve_session` at every UTC minute start in `[coverage_start, coverage_end)`. It collects adjacent open minutes into explicit intervals, including coverage-edge clipping.
- Restricted the bridge to the exact registered normal-hours `SessionCalendar` template and a nonempty trimmed version. Changed fields, overlays, lists in tuple fields, float weekdays and nondefault `time.fold` values fail with `ValueError`. Unsupported calendar objects/subclasses are rejected.
- Bridge endpoints must be whole UTC minutes; publication may retain microseconds. The bridge validates caller source before decorating it. Instrument is retained exactly as supplied, with no conversion or equivalence claim.
- Source provenance contains caller source, `calendar_sha256=<64 hex digits>`, and `RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH`. SHA-256 covers every calendar dataclass field using sorted compact JSON, ISO time strings and tuple-to-array encoding. Returned intervals retain the exact resolved behavior for downstream full-schedule hashing.

## Files changed by this worker

1. `trading_system/tree_replay/calendar.py` — new, 156 lines.
2. `tests/tree_replay/test_calendar.py` — new, 354 lines; 124 collected cases.
3. `.superpowers/sdd/2026-09-09-session-ema-history/task-1-report.md` — this report.

Only these three authored files were changed. Existing dirty work was preserved. No edits to `session_bars`, EMA, exports, configuration, exchange inbox/status, or other documentation. No subagents, commits, pushes, worktrees, feed/network calls, market payloads, dataset generation, model training or live effects.

Startup: read the brief first, then AGENTS/exchange README/protocol and own inbox. The sole Codex inbox request (`2026-08-31T090000Z-codex-architecture-review-and-routing.md`, sender Codex) was already `ACCEPTED_BY_CODEX`; its broad architecture/routing deliverables and phase verification commands are prior completed work, not an additional assignment. No inbox file was mutated. Used the TDD skill and `writing-good-tests.md`, and the implementer template's completeness/quality/discipline/testing self-review. The explicit user scope overrides the template's commit and exchange report destination defaults.

## TDD evidence

All test commands ran from `C:/Users/roeea/sagiv-repos/traders-engine`.

### Initial RED

Command:

```text
python -m pytest tests/tree_replay/test_calendar.py -q
```

Relevant exact output:

```text
E       ModuleNotFoundError: No module named 'trading_system.tree_replay.calendar'
117 failed in 1.76s
```

Exit: 1. All 117 cases failed at local imports because the requested module did not exist. Test collection and the actual local YAML calendar fixture succeeded; these were missing-feature failures, not malformed fixture or collection failures. No production sidecar existed before this run.

### Initial GREEN

Same exact command:

```text
python -m pytest tests/tree_replay/test_calendar.py -q
```

Exact output:

```text
........................................................................ [ 61%]
.............................................                            [100%]
117 passed in 0.79s
```

Exit: 0; no warnings.

### Self-review regression RED

Self-review identified Python equality accepting `(5.0,)` as `(5,)`, and ignoring `time.fold`. Added five rejection cases before changing production validation. Also added two supplementary checks for the complete literal provenance payload and delegation to the real resolver; these already passed and required no new behavior.

Command:

```text
python -m pytest tests/tree_replay/test_calendar.py -q
```

Relevant exact output:

```text
E       Failed: DID NOT RAISE <class 'ValueError'>
5 failed, 119 passed in 0.95s
```

Exit: 1. All five failures were `test_bridge_rejects_template_values_hidden_by_python_equality[changes0..4]`, demonstrating the exact-template validation gap.

### Final GREEN

After adding exact weekday element types and explicit fold validation:

```text
python -m pytest tests/tree_replay/test_calendar.py -q
```

Exact output:

```text
........................................................................ [ 58%]
....................................................                     [100%]
124 passed in 1.02s
```

Exit: 0; no warnings.

### Adjacent regression verification

Command:

```text
python -m pytest tests/tree_replay/test_calendar.py tests/tree_replay/test_bars.py tests/data_foundation/test_sessions.py -q
```

Exact output:

```text
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 73%]
........................................................................ [ 98%]
.....                                                                    [100%]
293 passed in 2.29s
```

Exit: 0; no warnings. Covers 124 new calendar cases, 161 existing bar cases and 8 existing resolver cases. Parent-owned session selector/EMA integration and the repository-wide suite were not claimed verified by this worker.

## Self-review

- Completeness: checked all interfaces and requirements against the task brief. Literal UTC assertions cover September 7's daily break, September 11–13's full weekend closure/reopen, March 8's 22:00 UTC Sunday opening and November 1's 23:00 UTC Sunday opening. Endpoint exclusion and single-minute coverage are covered.
- Quality: one focused module; existing normalization and resolver logic reused. No business-hours logic copied. Source serialization documents its format, and an independently written literal payload catches omitted calendar fields. The resolver spy delegates to the real resolver and checks both resulting intervals and the exact two minute-start calls.
- Discipline: authored only the permitted files, used synthetic instrument/time scenarios and the explicitly loaded local research calendar. No source/config loader is called inside the bridge. No readiness state is changed.
- Testing: initial RED/GREEN and self-review RED/GREEN recorded above. Boundary, malformed metadata, missing fields, timezone/fold normalization, immutability, canonical ordering, tiny gaps, unsupported template/overlay and publication provenance cases pass.
- Read both complete new-file diffs using `git diff --no-index -- NUL <path>` and inspected `git status --short`. The worktree already contained substantial unrelated changes, and parent-owned work continued appearing; none was reverted or edited.
- Whitespace checks: `git -c core.autocrlf=false diff --check --no-index -- NUL trading_system/tree_replay/calendar.py` and the same command for `tests/tree_replay/test_calendar.py` both emitted no whitespace diagnostics (exit 1 for new-file differences). Initial ordinary diff checks emitted only Git's existing LF-to-CRLF conversion advisory; no Git configuration was changed.
- Routine inspection corrections: discovered the real calendar fixture at `configs/data/session-calendar.yaml` after an initial nonexistent-path read; fixture loading succeeded before RED. This Windows PowerShell lacks `Get-Date -AsUTC`; the UTC report timestamp came from the clock tool instead. Neither issue affected test results or authored files.
- Findings fixed: exact-template equality loopholes described above. No remaining correctness findings or blockers for Task 1.

## Concerns and limits

No unresolved implementation concerns. The bridge intentionally supports only the supplied registered normal-hours template. It does not establish historical holiday/special-hours accuracy, execution truth, GC/CFD equivalence, data approval or readiness. Publication truth remains caller evidence. Current resolver/timezone database behavior is retained through exact output intervals, not asserted historically authoritative by the calendar field hash alone.

Runtime is linear in covered UTC minutes, as the brief requires; no multiyear performance certification was performed. Full schedule fingerprinting and EMA/session-bar use belong to the parent task. Human decisions needed for this bounded implementation: none.

Recommended next action: parent review/intake and integration verification using these interfaces.

## Fix1: reject timezone-bearing normal-template times

Status: DONE / awaiting scoped re-review by Descartes.

Request: parent relayed the Important review finding at `calendar.py:110`: a
`time` with `ZoneInfo("America/Chicago")` may compare equal to a naive template
time and serialize identically, passing the previous type/fold checks.

Changes:

- `trading_system/tree_replay/calendar.py`: the existing time-field guard now
  requires `tzinfo is None` as well as the expected fold. It applies to
  `regular_open`, `regular_close`, `daily_break_start` and `daily_break_end`
  before resolving minutes or computing provenance. Updated its comment.
- `tests/tree_replay/test_calendar.py`: added four parametrized rejection cases
  using `time(hour, tzinfo=ZoneInfo("America/Chicago"))`, one per field. Each
  requires a `ValueError` naming the offending field.
- This report: appended Fix1 evidence; preserved the earlier report as history.

TDD RED, before changing the production guard:

```text
python -m pytest tests/tree_replay/test_calendar.py -q

E       Failed: DID NOT RAISE <class 'ValueError'>
FAILED tests/tree_replay/test_calendar.py::test_bridge_rejects_timezone_bearing_template_times[regular_open-17]
FAILED tests/tree_replay/test_calendar.py::test_bridge_rejects_timezone_bearing_template_times[regular_close-16]
FAILED tests/tree_replay/test_calendar.py::test_bridge_rejects_timezone_bearing_template_times[daily_break_start-16]
FAILED tests/tree_replay/test_calendar.py::test_bridge_rejects_timezone_bearing_template_times[daily_break_end-17]
4 failed, 124 passed in 1.06s
```

Exit 1. All four cases reproduced the missing rejection; the previous 124 cases
passed. No fixture or collection failures.

TDD GREEN, after the guard change:

```text
python -m pytest tests/tree_replay/test_calendar.py -q

........................................................................ [ 56%]
........................................................                 [100%]
128 passed in 0.70s
```

Exit 0; no warnings. No broad suite was rerun.

Self-review: the additional predicate rejects any non-null timezone directly,
including date-dependent zones whose offset is unavailable on a bare time.
All four fields share this guard, and valid naive registered times continue
passing the existing literal interval, DST and provenance tests. The change
preserves resolver behavior and serialization for accepted inputs. TDD provided
the four reproductions before the two-line production/comment edit.

Only the same three scoped files were edited. Existing dirty work preserved;
no subagents, commits, external messages or other changes. No unresolved Fix1
concerns. Scoped change is ready for Descartes to review.

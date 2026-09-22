# Parent period aggregation report

Task2 requirements: docs/superpowers/plans/2026-09-09-period-state-and-ranges.md.
Implemented new periods.py, test_periods.py and DAILY-PERIOD-ASOF-USAGE.md.
No existing code modified. Literal synthetic cases cover forming/final OHLC,
late publication after end, exact full expected coverage, scheduled closures,
unresolvable fragments, missing/zero/overflow volume, future suffix invariance,
identity/provenance hashes, invalid inputs,23/25h daily boundaries.

RED: python -m pytest tests/tree_replay/test_periods.py -q --tb=short ->38failed,
all missing periods module, before implementation. GREEN samecommand:38passed
in1.60s, exit0. Existing selector baseline188passed in2.74s before changes.

Prices require cutoff=min(decision,end); publication cutoff remains decision.
Missing scheduled bars block OHLC. No ageing of a complete historical day.
No inference of holidays/broker boundaries; no partial lower bars/open-only ticks.
Both readiness flagsfalse, no model/outcome/live effect. No new domain rulings.
Source range worker remains independent; dependency integration is Task3.

## Task 2 review I1 fix (2026-09-09)

Request: fix Important finding I1 only in
`.superpowers/sdd/2026-09-09-period-state-and-ranges/task-2-review.md`, under
Task 2 of `docs/superpowers/plans/2026-09-09-period-state-and-ranges.md`.
Scoped fix worker; no nested agents, commits, worktrees or unrelated edits.
All edits used apply_patch; existing shared work and the report above preserved.

Root cause: temporal selection enforced epoch-grid alignment before checking
session overlap, although ClosedBar only requires exact timeframe duration.
In periods.py, classify overlap before enforcing alignment: a closure-only bar
remains in the temporally selected collection for exclusion/count diagnostics;
off-grid bars with any active-session overlap still raise ValueError, including
bars crossing either session edge. Input type, exact instrument/timeframe and
duplicate/revision checks remain before this classification. Session endpoint
validation and PERIOD_GRID_UNRESOLVED blockers are unchanged.

Added the review's exact 00:00-00:20 case with sessions 00:00-00:05 and
00:15-00:20, then a published 00:06-00:11 closure-only bar with extreme prices
and volume. It asserts unchanged OHLCV (100/108/99/106, volume 30), CLOSED,
no blocker or missing opens, two expected bars and excluded count 1. Three
additional cases retain rejection for off-grid bars contained in an active
session or overlapping its opening/closing edge.

Verification (run from repository root; no test warnings reported):

- RED, before the production fix:
  `python -m pytest tests/tree_replay/test_periods.py -q --tb=short -k 'closure_only_off_grid or off_grid_bars_overlapping'`
  -> 1 failed, 3 passed, 38 deselected in 1.58s; exit 1. The closure-only
  regression failed at periods.py:82 with
  `ValueError: selected bar opens must align to base grid`.
- GREEN, after the production fix, same focused command:
  `python -m pytest tests/tree_replay/test_periods.py -q --tb=short -k 'closure_only_off_grid or off_grid_bars_overlapping'`
  -> 4 passed, 38 deselected in 2.16s; exit 0.
- GREEN, complete covering test file:
  `python -m pytest tests/tree_replay/test_periods.py -q --tb=short`
  -> 42 passed in 1.20s; exit 0. Includes existing input validation and
  unresolved session-fragment cases.

Changed files: trading_system/tree_replay/periods.py,
tests/tree_replay/test_periods.py, and this appended report only.
I1 fix is ready for parent review; no fix blockers. Full-model/integration
acceptance remains outside this worker's scope; readiness flags remain false.

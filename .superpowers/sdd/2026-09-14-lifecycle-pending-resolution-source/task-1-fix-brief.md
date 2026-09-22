# Task 1 fix-round 1 brief

Read first:

- `.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-brief.md`
- `.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-report.md`
- `agent-exchange/reviews/2026-09-14T080000Z-lifecycle-pending-resolution-task1-review.md`

Only modify `tests/tree_replay/test_lifecycle_pending_resolution.py` and append
the required fix evidence to
`.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-report.md`.
Do not modify runtime production code, docs, pins, or unrelated files.

Address both review findings:

1. Replace/add physical, discriminating long/short extrema fixtures so a short
   test specifically needs high to reach `zone_low` (not low), and a long test
   specifically needs low to reach `zone_high` (not high). Include their
   discriminating no-touch counterparts. Record a mutation probe or an
   equivalent direct proof that a low/high swap would fail these tests.
2. Add one resolver-through-real-`TreeRevalidation` composition test. Supply
   real compatible raw ports rather than monkeypatching the resolver's
   `TreeRevalidation` constructor. It must prove the resolver can construct and
   invoke the accepted revalidator through the same `resolve` seam while still
   respecting this task's no-market-acquisition contract. Reuse in-memory,
   caller-supplied evidence only; do not invoke retained source or real I/O.

Run the original 67-test command plus every relevant new test. Do not use
subagents, commit or push. Use `apply_patch` for edits. Append RED/mutation and
GREEN evidence, changed files, and concerns to the report. Return status,
one-line test result, and report path only.

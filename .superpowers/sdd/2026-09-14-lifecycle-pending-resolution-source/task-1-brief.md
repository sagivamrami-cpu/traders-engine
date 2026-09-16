# Task 1 brief — PENDING resolution runtime

Read first: `docs/superpowers/plans/2026-09-14-lifecycle-pending-resolution-source.md`,
Task 1, and binding spec
`docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-INTAKE.md`.

## Deliverable

Create only:

- `trading_system/tree_replay/_vendor/lifecycle_pending_resolution.py`
- `tests/tree_replay/test_lifecycle_pending_resolution.py`
- `docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-USAGE.md`

Implement an offline `LifecyclePendingResolution(source)` with
`resolve(trade, *, state, price, bar_extremes) -> (messages, changed)`.

## Non-negotiable behavior

- Derive the entry band through the accepted helper. Touch uses source one-sided
  comparisons: short `high >= zone_low`; long `low <= zone_high`; absent symbol
  extreme means `(price, price)`. No touch mutates nothing and returns `([], False)`.
- Reuse `LifecycleOutcomeShelf` for `has_open` and `_outcome`,
  `LifecycleTransitions` for `_mark_terminal`, `_cancel_line`, `_fill_line`,
  `_fill_caveat`, and `TreeRevalidation` for `revalidate_pending`.
- On open-slot conflict: mark `CANCELLED`, append source cancellation message,
  write `{**trade, "result": "open_slot_conflict_at_fill"}`, return changed.
- On failed revalidation: same, with result `invalidated_at_fill` and its
  source reason. On success set source fields exactly, use one `now_epoch()`
  value for both fill/progress timestamps, append fill line + caveat, return
  changed, and write no outcome.
- `name` is `trade["symbol"].split(":")[-1]`; `side` is `SELL` only for
  direction `שורט`, else `BUY`.
- Do not load/save, lock, gate/deliver, fetch quotes/bars, invoke OPEN logic,
  calculate economics, produce labels/dataset rows, or claim readiness.
- Original retained source may only be read/parsed, never imported/executed.

## TDD and report

Write normal RED tests first and capture the failed command before production
code. Cover both directions, touch/no-touch, spot fallback, conflict/failed
validation/successful verified and unverified fill, state/clock/message/raw
outcome facts, and forbidden effects. Run the focused suite green afterward.

Do not use subagents. Do not commit or push. Write a full report using
`apply_patch` at
`.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-report.md`
including RED and GREEN commands/results, files changed, exact interface,
tests, and concerns. Return only DONE/DONE_WITH_CONCERNS/BLOCKED, a one-line
test result, and the report path.

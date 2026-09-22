# Final review brief — pinned outbox journal source component

## Scope

Review the complete additive outbox-journal source component as one unit:

1. `trading_system/tree_replay/_vendor/outbox_journal.py`
2. `tests/tree_replay/test_outbox_journal.py`
3. `docs/architecture/OUTBOX-JOURNAL-SOURCE-USAGE.md`
4. `trading_system/tree_spec/outbox_journal_source.py`
5. `tools/check_outbox_journal_source_parity.py`
6. `tests/tree_spec/test_outbox_journal_source.py`

Read the plan and contract first:

- `docs/superpowers/plans/2026-09-10-outbox-journal-source.md`
- `docs/architecture/OUTBOX-JOURNAL-SOURCE-CONTRACT.md`

Read both accepted task statuses and the task reviews:

- `agent-exchange/status/2026-09-13T232003Z-codex-outbox-journal-task1.md`
- `agent-exchange/status/2026-09-13T232003Z-codex-outbox-journal-task2.md`
- `agent-exchange/reviews/2026-09-10T201947Z-outbox-journal-task-review.md`
- `agent-exchange/reviews/2026-09-13T232003Z-outbox-journal-audit-review.md`

## Required judgments

Return separate **spec compliance** and **quality** verdicts.  Check that the
runtime is an offline, supplied-port projection of the pinned source, including
idempotent ID construction, append locking, malformed-row tolerance, LATE
filtering, state transitions, exact-text resolving and per-instance birth
memory.  Check that the audit actually proves the claimed projection and
inherited lifecycle-identity/tracker-admission dependency instead of merely
repeating a local copy.

Review the pending-duplicate birth-memory regression explicitly: a duplicate
PENDING must consume remembered birth time before a later new message with the
same ID is enqueued.  It is intentionally proven at both timestamps 120/180
and both ordinary/group-upgrade duplicate paths.

## Boundaries

Do not mistake a journal record for a broker send, replay certification, a
trade fill, economics, a dataset label or model readiness.  No original source
or replay runtime may be imported/executed.  Do not request new strategy
thresholds.  The component must retain `ready_for_replay=false` and
`ready_for_training=false`.

## Fresh controller evidence

After Task 2 review, the controller reran the 140-case component suite and the
external retained-source CLI.  Both passed: 140 tests in 22.38s; CLI VERIFIED
with zero blockers.  This final reviewer should inspect source/tests and may
run focused static checks, but need not repeat that reported suite.

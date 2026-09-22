# Agent Exchange Review

Reviewer: Codex

Target request: User request — read-only re-review of M1 lifecycle OPEN protection.

Created at: 2026-09-14T12:30:00Z

Status: REVIEW_READY_FOR_CODEX

Verdict: NOT ADDRESSED

Findings:

- **M1 remains open.** The four new target-only cases correctly establish that
  ordinary target movement must not cause an ambiguity outcome: each returns
  `([], False)` without changing the trade or writing an outcome fact under the
  current runtime.
- **They do not, however, catch a low/high swap through the runtime.** I
  monkeypatched only `LifecycleTransitions._ambiguous_touch` in memory with the
  all-directional-extrema swap, then called the public
  `LifecycleOpenProtection.resolve` path for the four physical target-only
  windows.  In every case both the source implementation and the mutant
  returned `([], False)`: `long-unhit`, `short-unhit`, `long-posthit`, and
  `short-posthit`.
- The repair report's claim that this mutant returns `True` for all four
  target-only windows is therefore contradicted by a direct runtime mutation
  probe.  The physical target-only tests are useful no-op coverage, but they
  cannot prove the claimed mutant-kill property on their own.
- **No new breakage observed.** The requested dependency-focused verification
  completed successfully with `46 passed in 0.86s`.

Open questions:

- None.  The next revision must add an executable mutation-sensitive test or
  test harness that fails under the specified low/high-swapped predicate, and
  must state precisely which mutation it kills.  It must not rely only on an
  unrecorded report claim.

Recommended next action:

- Revise the M1 repair tests, retain the useful target-only cases, and make the
  mutation proof executable through `LifecycleOpenProtection.resolve`.  Then
  rerun this same dependency-focused test command and request another
  read-only re-review.

Verification reviewed:

- Original finding: `agent-exchange/reviews/2026-09-14T120000Z-lifecycle-open-protection-task1-review.md`.
- Updated repair report:
  `.superpowers/sdd/2026-09-14-lifecycle-open-protection-source/task-1-report.md`.
- Runtime and test coverage:
  `trading_system/tree_replay/_vendor/lifecycle_open_protection.py`,
  `trading_system/tree_replay/_vendor/lifecycle_transitions.py`, and
  `tests/tree_replay/test_lifecycle_open_protection.py`.
- `python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_protection.py` — PASS, `46 passed in 0.86s`.
- Read-only in-memory runtime mutation probe — FAIL for the claimed proof:
  all four target-only windows produced `source=([], False)` and
  `swapped=([], False)`.


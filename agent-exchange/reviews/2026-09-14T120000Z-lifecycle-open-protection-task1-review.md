# Agent Exchange Review

Reviewer: Codex

Target request: User request — `Task1 lifecycle open protection` read-only review.

Created at: 2026-09-14T12:00:00Z

Status: REVIEW_READY_FOR_CODEX

Verdict: SPEC PASS; QUALITY FAIL

Findings:

- **Spec — PASS.** `LifecycleOpenProtection.resolve` is restricted to the
  source's conservative ambiguity branch at retained `tracker.py` lines
  2709–2715.  It derives `short`, the protective level, and the long/short
  ambiguity predicate through the accepted transition helper; for a true
  ambiguity it preserves source order: terminal state `STOPPED` when `hit` is
  empty, otherwise `DONE`; terminal message/result; one raw outcome fact; and
  `(message, to_group)` with `changed=True`.
- **Spec — PASS.** The helper's `_ambiguous_touch` has the same directional
  conditions as the retained source: long uses `low <= protective` and
  `high >= unhit_target`; short uses `high >= protective` and
  `low <= unhit_target`.  The post-hit cases retain the source's `DONE`
  outcome rather than converting them to `STOPPED`.
- **Spec — PASS.** A non-ambiguous supplied window returns `([], False)` prior
  to terminal mutation or outcome writing.  The runtime contains no ordinary
  OPEN ladder/progress/target handling, bar/quote acquisition, persistence,
  delivery, P&L, economic labelling, replay, dataset, training, or readiness
  behavior.  The usage document states these boundaries consistently.
- **M1 — QUALITY FAIL: long/short ambiguity tests do not detect a swapped
  `low`/`high` implementation.** All four ambiguity parameter cases use
  windows that satisfy both the correct predicate *and* its swapped-extrema
  mutant.  Independent calculation produced `correct=True,
  swapped_low_high=True` for `long-unhit`, `short-unhit`, `long-posthit`, and
  `short-posthit`.  Thus the comments at test lines 92–99 and the intended
  directional protection are not actually proved.  For example, a long case
  needs a protective touch only by `low` and a target touch only by `high`
  while the opposite extrema remain on the non-touch side; the short case
  needs the inverse.  Add asymmetric boundary tests for both unhit and
  post-hit paths before accepting Task 1.

Open questions:

- None for the specified Task 1 slice.  This review does not accept a source
  AST audit or CLI; the Task 1 report explicitly defers those items.

Recommended next action:

- Add the four asymmetric directional regression tests, first demonstrating
  that the swapped-extrema mutant fails, then rerun the same 42-test command
  and request a re-review.  No runtime behavior change is indicated by this
  finding.

Verification reviewed:

- `python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_protection.py` — PASS, `42 passed in 0.60s`.
- Retained pinned source inspected directly:
  `C:\\Users\\roeea\\AppData\\Local\\Temp\\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149\\chart-desk\\chartdesk\\tracker.py`, lines 2690–2715.
- Read-only inspection covered the intake, plan, Task 1 report, runtime,
  tests, and usage document.  No implementation files were changed, and no
  commit, push, or subagent was used.

# Agent Exchange Review

Reviewer: Codex (independent, read-only Task 1 review)

Target request: `.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-brief.md`

Created at: 2026-09-14T08:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdicts

- **Spec compliance: PASS.** The runtime is a correctly bounded projection of
  retained-source lines 2619-2646.  It derives `_entry_band`, uses the required
  one-sided touch expressions, preserves the conflict -> revalidation -> OPEN
  order, delegates to the accepted outcome/transition/revalidation helpers,
  snapshots the already-terminal record into the two raw outcome facts, and
  uses one `now_epoch()` value for both successful-fill timestamps.  It neither
  acquires evidence nor persists, gates, delivers, progresses OPEN, calculates
  economics, or claims readiness.
- **Quality: FAIL.** The focused suite passes, but its central direction/touch
  assertions cannot detect an accidental swap of the source `low` and `high`
  fields.  That leaves the core source rule unprotected and blocks a quality
  acceptance until the tests are corrected.

## Findings

### M1 — long/short touch tests do not distinguish the required source fields

`test_one_sided_touch_opens_both_directions_at_the_source_boundary` supplies
the short tuple `(99.0, 98.0)` and the long tuple `(102.0, 101.0)` for an XAU
entry of 100, whose accepted band is `(98.0, 102.0)`.  Both tuples are
nonphysical (`low > high`).  More importantly, they make the wrong field pass
as well:

- short: an erroneous `low >= zone_low` is still `99 >= 98`;
- long: an erroneous `high <= zone_high` is still `101 <= 102`.

The no-touch tuples also do not distinguish that mutation.  Therefore a
regression that exchanges the source rules — source line 2622 requires short
`high >= zone_low` and long `low <= zone_high` — remains green.  Use physical,
discriminating boundary bars in a follow-up, e.g. short `(97, 98)` and long
`(102, 103)`, with corresponding non-touch cases.

### M2 — revalidation is independently tested, but not exercised through this resolver seam

Every PENDING-resolver scenario replaces the module's `TreeRevalidation`
constructor through `monkeypatch` (`install_validation`, test file lines
112-115).  The 56 additional tests exercise the real `TreeRevalidation` class
separately; none executes `LifecyclePendingResolution.resolve` with the actual
accepted revalidator.  This is a legitimate deterministic seam for branch
tests, but it does not prove the resolver can construct and invoke the real
helper with a compatible supplied source.  Add one composed resolver fixture
using real revalidation inputs, while retaining the existing doubles for
precise cancellation/fill branch control.

### Verified observations

- The conflict branch calls the accepted terminal helper before creating
  `{**trade, "result": "open_slot_conflict_at_fill"}`; the failed-validation
  branch does the analogous `invalidated_at_fill` snapshot.  The tests confirm
  the post-terminal snapshot, including `resolved_ts`.
- A successful fill has no outcome write and assigns one supplied clock value
  to both `filled_ts` and `progress_ts`; this is directly covered.
- `short`, `name`, and `side` have the retained-source derivations.  The
  current implementation correctly evaluates the required high for short and
  low for long; M1 concerns the missing regression protection, not a present
  behavioral mismatch.
- Responsibility is correctly split: entry band, OPEN-slot lookup, terminal
  mutation/messages, raw outcome writing, and revalidation are reused from
  their accepted helpers.  No deferred OPEN-resolver behavior is present.

## Open questions

None for the Task 1 source slice.  The two test-quality repairs above are
engineering work, not a request for trader or human-domain policy.

## Recommended next action

Request a narrow Task 1 test-only repair for M1 and M2, then rerun this same
67-test bundle and repeat the independent review before accepting Task 1.

## Verification reviewed

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_tree_revalidation.py
67 passed in 4.99s
```

No code, tests, source pin, commit, push, or subagent was changed/used by this
review.

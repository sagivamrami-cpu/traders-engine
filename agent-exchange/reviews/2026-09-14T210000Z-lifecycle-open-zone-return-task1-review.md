# Task 1 review: lifecycle OPEN zone-return source

Reviewer: Codex

Target request: Direct user request for a read-only Task 1 review.

Created at: 2026-09-14T21:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

- Spec compliance: **FAIL** (M1 boundary contradiction)
- Task quality: **FAIL** (M2-M4 test gaps)

## Scope reviewed

- `.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-1-brief.md`
- `.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-1-report.md`
- `docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-INTAKE.md`
- `trading_system/tree_replay/_vendor/lifecycle_open_zone_return.py`
- `tests/tree_replay/test_lifecycle_open_zone_return.py`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-USAGE.md`
- Pinned retained `chartdesk/tracker.py` lines 1046-1106 and live-call boundary
  2751-2759, read as text only; never imported or executed.

## Findings

- **M1 — Spec boundary contradiction: the runtime can acquire data and cause
  effects through the real revalidation child.** The projection constructs
  `Revalidation(source)` at `lifecycle_open_zone_return.py:20-21` and invokes
  `still_valid()` at line 33. That accepted child calls
  `source.fetch_corrected()` at `revalidation.py:215`, `:254`, and `:261`, and
  its `_shadow()` path attempts filesystem writes through source ports at
  `revalidation.py:145-148`. The Task 1 brief and usage instead promise that
  the component never acquires market/revalidation data or produces effects.
  The focused tests replace `Revalidation` with `SuppliedRevalidation` before
  construction (`test_lifecycle_open_zone_return.py:72-74`), so their failing
  source ports prove only the substitute, not the shipped dependency graph.
  This is source-faithful to retained `_entry_recheck()` calling `still_valid`,
  but it cannot simultaneously satisfy the stated no-acquisition/no-effects
  Task 1 boundary. Resolve that contract explicitly: either make this slice a
  caller-supplied recheck-label port, or document and test the revalidation
  child acquisition/effect boundary rather than claiming it is absent.

- **M2 — Exact malformed-marker zero-target suppression is untested.** The
  retained and projected condition is `len(hit) <= said_targets`. The only
  malformed-marker case has one hit (`test_lifecycle_open_zone_return.py:163-172`),
  which proves rearm from a fallback zero but not the material `0 <= 0`
  suppression rule. Changing the runtime comparison to `<` still passes every
  current test but emits a duplicate notification for a malformed marker, a
  positive progress rung, and zero targets. Add that boundary regression and
  demonstrate the mutant fails.

- **M3 — The `DeskSuccess.reached()` half of exact excursion is untested.**
  All emitting cases derive their numerator from `progress_step`; none supplies
  a valid minimum-success proof with `progress_step=0`. Removing
  `desk_success.reached(trade)` from `_excursion()` would pass the suite while
  departing from retained line 1048. Add a valid accepted proof or a controlled
  desk-success child returning a positive rung, assert the marker numerator,
  and prove `0/0` stays silent only when both inputs are zero.

- **M4 — Message/journey construction has only partial assertions.** The tests
  assert the identity header and selected recheck substrings, but do not prove
  the optional journey is present and ordered before recheck, nor the retained
  spot/zone, original-stop distance, and unchanged-stop/targets advisory
  blocks. A removal or reordering of these retained lines 1097-1104 would
  pass. Add one fixture with reported progress and a stable recheck label that
  asserts the full source-order message sections. A direct valid-but-unverified
  recheck fixture would also distinguish that normal three-way label from the
  caught-error fallback, which currently happens to produce the same text.

## Confirmed source fidelity outside the findings

The implementation otherwise mirrors the retained helper: it forms
`max(progress_step, desk_success.reached)/len(hit)`, returns early for `0/0`,
uses malformed marker fallback zero, preserves target-count-only rearm, applies
the short `spot >= zone_low` / long `spot <= zone_high` band predicates, builds
the source journey/recheck/footer sequence, and writes only `zone_return_at`
inside its own body. Its `resolve()` output matches the retained live boundary:
one `(message, to_group)` append and `changed=True` only when a message exists.
It adds no outcome, target, protective, terminal, persistence, or delivery
operation directly. The M1 child call prevents accepting the stronger claimed
no-data/no-effects boundary.

## Recommended next action

Resolve M1 as a contract/design decision before acceptance, then add M2-M4
regressions (with demonstrated failing mutants) and rerun the focused runtime
and direct-helper suites. No source checkout execution, replay, outcome,
economic, dataset, model, or live-trading claim is supported by this review.

## Verification reviewed

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider
```

PASS: `164 passed in 5.14s`.

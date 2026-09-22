# M1 re-review: lifecycle OPEN minimum-success Task 1

Reviewer: Codex

Target request: Direct user request for a scoped, read-only M1 re-review of `2026-09-14T180000Z-lifecycle-open-minimum-success-task1-review.md`.

Created at: 2026-09-14T18:30:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

**ADDRESSED.**

## Evidence

- The new regression, `test_existing_bar_minimum_suppresses_an_otherwise_eligible_quote`, supplies an existing `minimum_message="bar-minimum"` and an otherwise eligible quote: matching `lp == spot`, `price_ts = NOW - 10`, post-fill (`filled_ts = NOW - 60`), no forming-bar-extremes membership, and no protective touch. It asserts that `bar-minimum` remains the one returned message, `trade` gains no `minimum_success` quote proof, and one raw result is written.
- The current runtime retains the required first quote-gate conjunct, `not minimum_message`, before it can call `DeskSuccess.observe(..., "exact_venue_quote")`. The bar-message test's exact source-port trace contains only `outcomes_mkdir`, one `now_epoch`, and `open_outcomes`; the clock call belongs to the one raw-outcome shelf write. This preserves the no-quote branch and source-clock bounds for an existing bar message.
- I independently exercised the exact mutant in memory without changing workspace files: replaced the sole occurrence of `not minimum_message and ` in `lifecycle_open_minimum_success.py`, then invoked the new test. It raised `AssertionError` (`MUTANT_RED`); the mutant therefore cannot survive the regression.
- Fresh focused/helper verification passed with no failures:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py
```

Result: `96 passed in 0.65s`.

## Scope and boundaries

This re-review addresses only the M1 regression gap from the prior Task 1 review. It does not accept Task 2 source auditing/CLI, ambiguity or ordinary OPEN resolution, composed resolver/caller behavior, persistence/delivery, fills or economics, replay, datasets, training, models, or live-trading readiness.

## Open questions

None within the requested M1 scope.

## Recommended next action

The M1 finding is closed; continue the existing Task 1 review/acceptance flow under its stated boundaries.

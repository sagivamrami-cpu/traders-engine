# Task 1 M1 Fix Report

## Scope

Fix only M1 from
`agent-exchange/reviews/2026-09-14T070000Z-lifecycle-live-resolution-evidence-task1-review.md`:
an active symbol whose present raw quote mapping is `None` must normalize to
`{}` before its timestamp is read, preserving the retained source expression
`_q.get(symbol) or {}` and allowing supplied corrected-bar fallback.

## Changed files

- `tests/tree_replay/test_lifecycle_live_resolution_evidence.py`
  - Added `test_collector_uses_corrected_fallback_when_active_symbol_quote_is_none`.
- `trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py`
  - Changed only raw quote age lookup to
    `(raw_quotes.get(symbol) or {}).get("ts", 0)`.

## TDD evidence

1. Before the runtime edit:

   ```text
   python -B -m pytest tests/tree_replay/test_lifecycle_live_resolution_evidence.py -q -k quote_is_none
   1 failed, 12 deselected in 2.59s
   ```

   The collector returned `({}, {})` instead of the supplied corrected close
   and extrema.

2. After the minimal runtime edit:

   ```text
   python -B -m pytest tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py -q
   30 passed in 2.07s
   ```

3. `git diff --check` exited successfully. It emitted only pre-existing line
   ending warnings for unrelated `AGENTS.md` and `README.md` working copies.

## Boundaries retained

No resolver/state transition, market-data access, replay, outcome/economic
label, dataset, training, model, commit, or push behavior was changed.

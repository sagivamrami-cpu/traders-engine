# Task 1 review: lifecycle OPEN minimum-success source

Reviewer: Codex

Target request: Direct user request for a read-only Task 1 review.

Created at: 2026-09-14T18:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

- Spec compliance: **PASS**
- Task quality: **FAIL** (M1 test gap)

## Scope reviewed

- `.superpowers/sdd/2026-09-14-lifecycle-open-minimum-success-source/task-1-brief.md`
- `.superpowers/sdd/2026-09-14-lifecycle-open-minimum-success-source/task-1-report.md`, including its fix round
- `docs/architecture/LIFECYCLE-OPEN-MINIMUM-SUCCESS-SOURCE-INTAKE.md`
- `docs/superpowers/plans/2026-09-14-lifecycle-open-minimum-success-source.md`
- `trading_system/tree_replay/_vendor/lifecycle_open_minimum_success.py`
- `tests/tree_replay/test_lifecycle_open_minimum_success.py`
- `docs/architecture/LIFECYCLE-OPEN-MINIMUM-SUCCESS-SOURCE-USAGE.md`
- Pinned retained `tracker.py` lines 2690-2704, read as text only; never imported or executed.

## Findings

- **Spec PASS.** The runtime preserves the retained branch order: derive the protective touch from supplied `low`/`high`; try the quote branch only before any minimum exists and while protection is untouched; derive progress using `low` for short and `high` for long; write source minimum points; construct the one message; then append one raw `minimum_success` outcome. The fix round correctly moved message-list construction before the outcome call, matching retained lines 2702 then 2703.
- **Spec PASS.** The quote gate is exact: supplied quote `lp == spot`, inclusive `0 <= now - quote_ts <= 120`, quote timestamp no earlier than fill time, no supplied forming-bar-extremes membership, no protective touch, and no pre-existing minimum message. It reads the supplied source clock at the same one-or-two direct branch sites as retained `time.time()` (the second only when `filled_ts` is absent); it does not acquire quotes, bars, or the membership map.
- **Spec PASS.** `DeskSuccess`, `LifecycleTransitions`, and `LifecycleOutcomeShelf` are the accepted helpers. The raw outcome is `{**trade, "result": "minimum_success"}` through the shelf port; it is not converted into a terminal, economic, replay, dataset, training, model, or delivery claim. The usage document states the supplied-evidence and pre-ambiguity boundaries accurately.
- **M1 QUALITY FAIL — no regression proves that an existing bar minimum suppresses an otherwise eligible quote.** `test_existing_bar_minimum_records_one_raw_fact_and_uses_directional_best_for_progress` passes `minimum_message="bar-minimum"` but leaves `quote` empty. Removing `not minimum_message` from the quote gate would therefore still make every current test pass: the empty quote fails independently. The source requirement is material—when a bar message already exists, a fresh matching post-fill quote must not call `observe`, replace that message/proof, or alter its source. Add a test with `minimum_message="bar-minimum"` and a fresh, matching, post-fill eligible quote; assert the returned message remains `bar-minimum`, no `exact_venue_quote` proof is created/replaced, exactly one raw fact is written, and the direct source-clock use stays limited to the retained branch behavior. Demonstrate the mutant fails before re-review.

## Recommended next action

Add the M1 precedence regression (RED against a removed `not minimum_message` guard, then GREEN), rerun the focused component and helper suites, and request a Task 1 re-review. No runtime behavior change is indicated.

## Verification reviewed

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py
```

PASS: `95 passed in 0.65s`.

## Boundaries retained

This review does not accept Task 2 source auditing/CLI, ambiguity, protective or target resolution, ordinary progress, zone return, a composed resolver/caller, persistence, delivery, fills/P&L/economics, replay, datasets, training, models, or live-trading readiness.

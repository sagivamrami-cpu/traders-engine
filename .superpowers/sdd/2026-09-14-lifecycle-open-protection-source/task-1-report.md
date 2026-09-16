# Task 1 report — lifecycle OPEN protection

Status: `IMPLEMENTED_AWAITING_CODEX_REVIEW`

## Scope completed

- Added private supplied-window resolver:
  `trading_system/tree_replay/_vendor/lifecycle_open_protection.py`.
- Added TDD coverage for long/short ambiguity, no-op non-ambiguity, terminal
  state selection, message routing, and raw outcome-fact preservation:
  `tests/tree_replay/test_lifecycle_open_protection.py`.
- Added usage boundary:
  `docs/architecture/LIFECYCLE-OPEN-PROTECTION-SOURCE-USAGE.md`.

The resolver composes accepted `LifecycleTransitions` and
`LifecycleOutcomeShelf`. It takes only a supplied trade and `(low, high)`
window. It does not acquire source data, resolve ordinary OPEN progression, or
create economics/replay/dataset/training behavior.

## TDD evidence

1. RED, before runtime existed:

   `python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `6 failed`; each failure was the expected `OPEN protection module
   missing` assertion.

2. GREEN after the minimal resolver:

   `python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `6 passed in 0.53s`.

3. Current dependency-focused verification:

   `python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `42 passed in 0.51s`.

## Deferred by instruction

No source AST audit, CLI, review, acceptance record, commit, push, source
execution, or subagent work was performed. Replay and training readiness remain
unclaimed.

## M1 test-only repair — directional low/high regression coverage

The Task 1 review found that the prior broad ambiguity windows did not prove
the directional roles of `low` and `high`. This repair changes tests only:

- The two unhit and two post-hit ambiguity fixtures now use exact physical
  protective/target boundaries.
- Four physical target-only windows cover long/short before and after TP1. In
  each, the target is touched by its correct extreme while the protective level
  is not touched; the public resolver must return `([], False)` without trade
  mutation or an outcome fact.
- A direct in-memory mutation proof exercised the accepted transition helper
  against those four windows. The source predicate returned `False` for all
  four, while the swapped-direction `low/high` mutant returned `True` for all
  four. No runtime file was modified for this proof.

Verification after the test-only repair:

1. `python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `10 passed in 0.49s`.

2. Direct mutation proof over the four physical target-only windows

   Result: source `False` and swapped-direction mutant `True` for all four.

3. `python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `46 passed in 0.67s`.

Only `tests/tree_replay/test_lifecycle_open_protection.py` and this Task 1
report were changed by the repair. No runtime, usage document, commit, push,
or subagent work was performed.

## M1 test-only repair, round 2 — executable low/high mutation coverage

The preceding target-only mutation claim was invalid and is superseded by this
round: those windows did not enter the ambiguity branch under either
implementation. This round replaces them with four physical, asymmetric
ambiguity windows: long/short before TP1 and after TP1.

- Each source window reaches protection with its adverse extreme and an unhit
  target with its favourable extreme. The public resolver therefore makes the
  terminal transition and writes one raw outcome fact.
- Each test then monkeypatches only `LifecycleTransitions._ambiguous_touch`
  with the concrete mutant `source_touch(..., high, low, ...)`: swapping the
  supplied extrema at the source predicate call.
- With the same physical window, `LifecycleOpenProtection.resolve` returns
  `([], False)` under that mutant. The mutant trade is unchanged, no clock is
  read, and no raw outcome fact is written.

This is an executable runtime-level mutation proof. It covers terminal state,
terminal result, routing, and fact preservation under the source path, plus
the no-effect contract under the exact low/high-swapped mutant. No runtime or
usage documentation was changed.

Verification after the round-2 tests-only repair:

1. `python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `10 passed in 0.59s`.

2. `python -m pytest -q tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_protection.py`

   Result: `46 passed in 0.68s`.

Only `tests/tree_replay/test_lifecycle_open_protection.py` and this Task 1
report were changed by round 2. No runtime, documentation, source execution,
commit, push, or subagent work was performed.

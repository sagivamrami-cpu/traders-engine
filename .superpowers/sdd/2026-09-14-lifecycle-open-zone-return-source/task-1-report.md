# Task 1 report — lifecycle OPEN zone-return source

## Scope

Implemented only the private supplied-spot notification projection required by
Task 1. No retained source was imported or executed. No static auditor, CLI,
resolver composition, market-data acquisition, persistence, delivery, outcome
write, economic behavior, commit, push, or subagent work was added.

## Changed files

- `trading_system/tree_replay/_vendor/lifecycle_open_zone_return.py`
- `tests/tree_replay/test_lifecycle_open_zone_return.py`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-INTAKE.md`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-USAGE.md`
- `docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md`

## TDD evidence

### RED

Command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

Before runtime creation: `14 failed in 0.21s`. Every failure was the expected
`OPEN zone-return resolver module missing` assertion.

### GREEN

The minimal runtime now composes accepted entry-band, transition/journey,
`DeskSuccess`, voice, and `Revalidation` helpers. The same focused command
passes:

```text
14 passed in 0.48s
```

The tests cover long/short band edges, outside-band no-op, no excursion,
repeat suppression, target-only rearm, malformed marker handling, all required
recheck labels, and mutation/effect-port isolation.

During the first GREEN run, two assertions were corrected after root-cause
checking against the retained source and accepted voice helper: an invalid
marker with zero hit targets remains suppressed by the source's `<= 0` rule,
and `voice.check(..., False)` emits `❗️`. The runtime did not change in that
correction; the focused suite subsequently passed.

## Boundary result

`resolve(trade, *, spot)` returns either `([], False)` or exactly one
`(message, trade["to_group"])` and `True`. A successful message changes only
`trade["zone_return_at"]`; the recheck remains advisory text and cannot veto
the OPEN lifecycle state.

## Fix round 1 — controller boundary ruling and regressions

The runtime intentionally remains unchanged. It already constructs the actual
`Revalidation(source)` child and calls `still_valid(trade)`; replacing it with
a precomputed label port would break source fidelity. The corrected intake,
usage, and plan state that the accepted child may fetch corrected evidence and
attempt source-owned shadow writes through supplied offline ports. Zone-return
itself remains label-only: it makes no direct terminal/outcome/persistence/
delivery decision and mutates only `zone_return_at` on emission.

### Added regression coverage

- A method spy on the actual `Revalidation` class proves the constructed child
  receives and calls `still_valid(trade)`.
- A malformed marker with zero hit targets remains suppressed by the source's
  exact `len(hit) <= 0` rule.
- A complete identity-bound `DeskSuccess` proof arms `1/0` when
  `progress_step` is zero.
- One full literal message asserts spot then zone, original stop-distance,
  journey before recheck, and the unchanged stop/targets footer. A separate
  direct-valid-unverified case retains its reason while the caught-error label
  has no reason.

### Mutation RED evidence

Each temporary runtime mutation was reverted immediately after its targeted
test failed:

```text
Revalidation call -> static tuple:
  test_actual_revalidation_child_boundary_is_called_for_the_advisory_label
  1 failed (spy calls were [])

len(hit) <= said_targets -> len(hit) < said_targets:
  test_malformed_marker_with_zero_targets_suppresses_the_same_excursion
  1 failed (a duplicate message emitted)

DeskSuccess.reached(trade) -> 0:
  test_valid_desk_success_arms_a_zero_progress_step_excursion
  1 failed ((0, False) instead of (1, True))

journey/recheck source order swapped:
  test_full_message_keeps_source_order_and_direct_unverified_recheck_reason
  1 failed (literal source-order message mismatch)

caught error reason -> "direct unverified reason":
  test_direct_valid_unverified_reason_is_distinct_from_caught_error_label
  1 failed (fallback incorrectly contained the direct reason)
```

The new focused runtime tests pass against the restored source-faithful code:

```text
19 passed in 0.75s
```

The required focused-plus-direct-helper verification also passed:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider
```

```text
169 passed in 5.23s
```

## Status-check rerun — exact current artifact evidence

The updated focused artifact was read before rerun. No runtime/documentation
change was required beyond the already recorded fix-round work. Each temporary
mutant was restored immediately after its named test failed again:

```text
Revalidation call -> static tuple:
  test_actual_revalidation_child_boundary_is_called_for_the_advisory_label
  1 failed (spy calls were [])

len(hit) <= said_targets -> len(hit) < said_targets:
  test_malformed_marker_with_zero_targets_suppresses_the_same_excursion
  1 failed (a duplicate message emitted)

DeskSuccess.reached(trade) -> 0:
  test_valid_desk_success_arms_a_zero_progress_step_excursion
  1 failed ((0, False) instead of (1, True))

journey/recheck source order swapped:
  test_full_message_keeps_source_order_and_direct_unverified_recheck_reason
  1 failed (literal source-order message mismatch)

caught error reason -> "direct unverified reason":
  test_direct_valid_unverified_reason_is_distinct_from_caught_error_label
  1 failed (fallback incorrectly contained the direct reason)
```

Restored GREEN verification:

```text
tests/tree_replay/test_lifecycle_open_zone_return.py: 19 passed in 0.63s
focused plus DeskSuccess/lifecycle-transition/Revalidation helpers:
169 passed in 5.67s
```

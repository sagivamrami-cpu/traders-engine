# Task 1 report — PENDING resolution runtime

## Status

DONE_WITH_CONCERNS — the scoped offline runtime, its focused tests, and its
usage boundary are implemented. Source-parity auditing and independent review
are intentionally Task 2 / subsequent acceptance work and have not been
claimed here.

## Interface

`LifecyclePendingResolution(source).resolve(trade, *, state, price,
bar_extremes) -> (messages, changed)` accepts one supplied mutable PENDING
record and caller-supplied state/evidence. It returns a list of
`(message, to_group)` tuples and a change flag.

The implementation composes the accepted entry-band helper,
`LifecycleOutcomeShelf`, `LifecycleTransitions`, and `TreeRevalidation`.
It preserves the source branch order: one-sided touch, OPEN-slot conflict,
fill-time revalidation failure, then OPEN transition. Successful fills use
one `now_epoch()` reading for both `filled_ts` and `progress_ts`; they write
no outcome row. The two cancellation paths write the source raw facts only.

## TDD evidence

RED command, before the runtime existed:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py
11 failed in 0.21s
```

The failure was the expected missing-module assertion:
`PENDING resolution module missing`.

GREEN focused command:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py
11 passed in 0.48s
```

GREEN composed runtime command:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_tree_revalidation.py
67 passed in 8.76s
```

## Tests covered

- Short and long one-sided boundary touches, plus the absent-extreme spot
  fallback.
- Strict no-touch immutability and no revalidation/outcome/clock effects.
- Same-symbol/same-direction OPEN conflict cancellation and its raw outcome
  fact.
- Failed revalidation cancellation, source reason, and its raw outcome fact.
- Verified and unverified successful fill fields, one shared timestamp,
  message caveat, and no fill outcome.
- Explicit failing raw ports for load/save/lock, quote/bar fetch, gate/delivery
  and deferred OPEN logic.

## Files changed

- `trading_system/tree_replay/_vendor/lifecycle_pending_resolution.py`
- `tests/tree_replay/test_lifecycle_pending_resolution.py`
- `docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-USAGE.md`

## Concerns / deferred scope

The revalidation-result scenarios use a narrow deterministic test double at
the accepted `TreeRevalidation` boundary; its real behavior is separately
covered by the composed runtime suite. Task 1 does not run the retained source
or certify source parity. It does not load/save, lock, acquire market data,
gate/deliver, advance OPEN logic, calculate economics, create labels/dataset
rows, train a model, or establish replay/training readiness.

## Fix round 1 — test-only review repair

Status: DONE_WITH_CONCERNS. Only the permitted test file and this appended
report were changed; runtime, documentation, pins, and retained source were
not modified or executed.

### Mutation / direct-proof evidence

`test_physical_extrema_fixtures_discriminate_the_source_touch_field` uses
hand-derived, physical bars around the known XAU entry band `(98.0, 102.0)`:

- short touch `(97.0, 98.0)` requires `high >= zone_low`; the swapped
  `low >= zone_low` expression is false;
- long touch `(102.0, 103.0)` requires `low <= zone_high`; the swapped
  `high <= zone_high` expression is false;
- physical no-touch counterparts `(97.0, 97.999)` and `(102.001, 103.0)`
  preserve the strict source boundaries.

This is the equivalent direct mutation proof required by the review: replacing
the resolver's required field with the opposite extreme makes each touch
fixture false. It is intentionally a test-only proof rather than a temporary
runtime mutation, because this repair forbids runtime edits.

Focused mutation/direct-proof plus real-composition command:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py -k "physical_extrema or real_revalidator"
5 passed, 11 deselected in 1.14s
```

### Real revalidation composition

`test_resolver_composes_the_real_revalidator_over_in_memory_raw_ports` no
longer replaces the resolver's `TreeRevalidation` constructor. It constructs
the real accepted revalidator through `LifecyclePendingResolution.resolve`,
using only the in-memory `Inputs` raw-port fixture already used by the
revalidation suite. The assertion observes the real supplied-frame read
(`15m`, `10`) and successful OPEN fill; it invokes neither retained source nor
real I/O, and the resolver does not acquire quote/bar evidence outside the
accepted revalidator seam.

### GREEN evidence

Original combined command, including every new relevant test:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_tree_revalidation.py
72 passed in 8.18s
```

### Changed files

- `tests/tree_replay/test_lifecycle_pending_resolution.py`
- `.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-1-report.md`

### Remaining concerns

The focused resolver branch tests retain narrow revalidation doubles for their
branch-specific outcomes; the added composition case closes the constructor /
real-helper seam without broadening this Task 1 slice. Source-parity audit,
outer resolver behavior, persistence, economic outcomes, dataset construction,
and model training remain outside this repair.

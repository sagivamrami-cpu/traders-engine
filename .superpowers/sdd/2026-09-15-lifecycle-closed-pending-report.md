# Closed-bar PENDING resolver — Task 1 report

## Scope

Implemented only `LifecycleClosedPendingResolution`, the PENDING portion of the
closed 15-minute-bar lifecycle source slice. Source authority was
`docs/architecture/LIFECYCLE-CLOSED-PENDING-SOURCE-INTAKE.md` and retained
`chartdesk/tracker.py` lines 1174–1264 from the pinned chart-desk checkout,
read as text.

## TDD evidence

The focused test module was added before the runtime module existed.

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_closed_pending_resolution.py
7 errors ... AssertionError: closed PENDING runtime missing
```

After the smallest runtime implementation:

```text
7 passed in 0.48s
```

The focused tests cover expiry plus hand-checked long/short missed-R movement,
raw expiry fact and shelf write, untouched preservation, slot conflict,
revalidation cancellation with pass clock, stop ambiguity, and a successful
fill that returns OPEN for a later resolver.

## M1 clock-separation correction

The review found that the first projection reused the caller-supplied pass
anchor for `filled_ts` and `progress_ts`. The retained source instead makes a
fresh clock read when a fill transitions to OPEN. The runtime now preserves the
supplied `now` for expiry and `revalidate_pending(..., now=now)`, then uses
`source.now_epoch()` only for the fill timestamps.

Test first:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_closed_pending_resolution.py
1 failed, 7 passed
AssertionError: filled_ts == NOW, expected NOW + 37.0
```

After the one-line correction:

```text
8 passed in 0.60s
```

Mutation evidence: temporarily restoring the erroneous
`filled_ts = progress_ts = float(now)` caused the new clock-separation test to
fail (`1 failed, 7 deselected`), then the source-clock implementation was
restored.

## Regression

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_closed_pending_resolution.py \
  tests\\tree_replay\\test_lifecycle_pending_resolution.py \
  tests\\tree_replay\\test_lifecycle_outcome_shelf.py \
  tests\\tree_replay\\test_lifecycle_transitions.py \
  tests\\tree_replay\\test_tree_revalidation.py
80 passed in 8.84s
```

## Explicit exclusions

No source auditor/CLI, caller binding, bar acquisition, OPEN progression,
persistence/gating, delivery, replay, economics, dataset, training, model, or
live-trading readiness claim was implemented.

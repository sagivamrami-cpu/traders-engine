# Closed-bar PENDING runtime review

Reviewer: Codex

Target request: Read-only review of `LifecycleClosedPendingResolution` against
the retained `chartdesk/tracker.py` PENDING slice, lines 1174–1264.

Created at: 2026-09-15T02:00:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict: **FAIL**

## Finding

### M1 — fill timestamps use the wrong clock

The retained source captures `now = time.time()` once at line 1123 for the
pass/expiry/revalidation clock, then deliberately takes a *new* clock reading
at the actual fill transition:

```python
t["filled_ts"] = t["progress_ts"] = time.time()  # source line 1249
```

The projection instead writes the caller's pass anchor:

```python
trade["filled_ts"] = trade["progress_ts"] = float(now)
```

at `lifecycle_closed_pending_resolution.py:72`. A slow correction/revalidation
or a caller whose supplied pass clock differs from its source clock therefore
produces a different causal fill timestamp. This is not merely formatting:
later OPEN processing derives its post-fill window from `filled_ts`.

The existing successful-fill and ambiguity tests set `Source.now == now`, so
they do not distinguish the two clocks. Add a regression with a supplied pass
clock different from the source's current clock, and assert the exact source
fill-clock behavior before accepting this component.

## Verified alignment outside M1

- Expiry is strictly `>` the style/variant expiry, only for an untouched entry;
  the missed movement uses the first `since["open"]`, directional aggregate
  extreme, raw `expired` fact, rounded values and shelf write.
- Touch geometry matches source inclusively: short `high >= zone_low` and
  `high >= stop`; long `low <= zone_high` and `low <= stop`.
- A touched plan checks OPEN-slot conflict before revalidation, revalidates with
  the supplied pass clock, and writes the source raw cancellation facts.
- Entry plus stop in the same aggregate window transitions through fill fields
  and then conservatively reaches terminal `STOPPED` with raw
  `stopped_ambiguous`.
- A successful non-ambiguous fill remains `OPEN` and returns only the fill
  indication, preserving the narrow fall-through contract for a later OPEN
  resolver. This review makes no claim about that later resolver, acquisition,
  persistence, delivery, replay, economics, dataset, training, model, or live
  trading.

## Verification reviewed

- Read as text only: retained `chartdesk/tracker.py` at pinned commit
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, verified tracker blob
  `b616b34022e436545d8c1daf85eced51614fd74e`, lines 1119–1264.
- Read: source intake, Task 1 report, runtime, tests, and usage contract.
- Current regression run:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_closed_pending_resolution.py \\
  tests\\tree_replay\\test_lifecycle_pending_resolution.py \\
  tests\\tree_replay\\test_lifecycle_outcome_shelf.py \\
  tests\\tree_replay\\test_lifecycle_transitions.py \\
  tests\\tree_replay\\test_tree_revalidation.py
79 passed in 11.03s
```

The green tests are insufficient to accept the component until M1 is fixed and
covered by a discriminatory test.

## Recommended next action

Make the fill timestamp an explicit source-clock projection distinct from the
pass anchor, add the clock-separation regression, then request a focused
re-review. No production code was changed by this review.

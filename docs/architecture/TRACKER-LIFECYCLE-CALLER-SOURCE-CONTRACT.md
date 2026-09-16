# Tracker lifecycle caller — source contract

## Purpose and authority

This is the narrow caller seam after the accepted lifecycle gate/parking
component. It projects only the stateful ordering at the end of the pinned
`chart-desk/tracker.py` closed-bar `check()` and live `_check_live_locked()`
paths, plus the public `check_live()` lock-skip wrapper.

Authority is chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`,
tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`, retained and parsed
as text only. The relevant source tails are:

```python
if changed:
    out = _persist_gated_lifecycle(out, d)
    _save(d)
return out
```

The public live wrapper acquires `_locked(skip_if_busy=True)` and returns `[]`
only for `LockBusy`; it does not run the resolver or gate in that case.

## Runtime boundary

`TrackerLifecycleCaller(source)` owns one accepted `LifecycleGate(source)`.
The source context owns and exposes the process-shared `TrackerLock` policy
through `source.locked(...)`; the caller does not construct a lock. It exposes
`check(resolve)`, `_check_live_locked(resolve)`, and `check_live(resolve)`.

`check` loads tracker state once, returns `[]` when it is empty, calls the
supplied unported closed-bar mutation kernel with mutable state, and commits
only when its actual `(out, changed)` result says changed.
`_check_live_locked` has identical load/mutate/commit semantics for a live
kernel and assumes its lock is already held. `check_live` wraps only that
method with the source-owned shared lock policy. Its source-faithful broad
`try`/`with`/`except LockBusy` boundary returns `[]` for a busy lock and also
for a `LockBusy` raised by the resolver inside the live pass; it does not gate
or save after that resolver error. Every non-`LockBusy` failure propagates.

The callback receives actual mutable state and raw evidence through the same
offline source. It cannot return a gate result, journal row, saved-state
result, receipt result or delivery confirmation. It returns exactly
`(list[tuple[str, bool]], bool)`; runtime validates this shape before effects.

When `changed is True`, `_commit` calls real
`LifecycleGate._persist_gated_lifecycle(out, state)` before `source.save(state)`
and returns the gate method's returned `out`. When false, it returns raw `out`
without gate or state write. The original source gate itself returns raw output,
not a transport receipt.

The initial seam does not implement corrected-bar fetch/coverage/staleness,
fill geometry, open-slot arbitration, revalidation, target/stop/progress or
management, outcome writes, quote fallback, tape attribution or a causal
scheduler/checkpoint. Those remain source closures. `replay_parked()` is not
sent or implicitly committed here: source says an outer pass must re-offer it
through the gate in the correct context.

## Raw effects and limits

The same offline source provides accepted lifecycle-gate ports plus `load`,
`save` and accepted lock ports. No fallback accesses a filesystem, network,
broker, queue or transport. A lock skip is an observable no-op, not retry.

This is not a complete tracker caller, replay, delivery, fill, trade economics,
outcome labels, dataset, model training, promotion or live action. Audit
`ready_for_replay` and `ready_for_training` stay false.

## Independent source proof

The auditor pins baseline commit/blob and parses selected source tails/wrapper
without importing retained source. It checks changed-only persistence order and
the `LockBusy` boundary, runtime AST/interfaces, actual lifecycle-gate and
tracker-lock child audits, and false readiness. Its explicit-root JSON CLI exits
zero only when every check is verified.

# Tracker lifecycle caller — source intake

Read-only intake following lifecycle gate/park implementation. It does not
implement a full caller, causal scheduler or replay.

## Authority

Pinned chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`,
`chartdesk/tracker.py` blob `b616b34022e436545d8c1daf85eced51614fd74e`.
The source was inspected as text only.

## Actual persistence order

The closed-bar `check()` path loads tracker state once, advances eligible rows
from corrected 15-minute bars, emits `(message, to_group)` tuples and marks
`changed`. Only on a change it executes:

```text
out = _persist_gated_lifecycle(out, d)
_save(d)
return out
```

Thus gate/journal effects happen after mutation of in-memory state but before
the tracker-state save. `_persist_gated_lifecycle` itself returns original
`out`, not its admitted subset. The caller's returned tuples therefore are not
delivery confirmations; later caller transport still owns send behavior.

The live-price resolver `_check_live_locked()` follows the same changed-only
gate-then-save order. Its public `check_live()` wrapper acquires the resolver
lock with skip-on-busy behavior and returns `[]` on `LockBusy`; no gate is run
for a skipped pass. This lock/clock distinction is source behavior and cannot
be replaced with a generic caller loop.

## Non-equivalent paths

`manage_open()` / `_manage_open_locked()` also mutate and save tracker state but
do not call `_persist_gated_lifecycle` in this source location. `revival_check`
operates a separate shelf/revalidation flow; `near_entry_alerts` is a pending
proximity path. None may silently be routed through this gate merely because it
returns text. Their caller/order and delivery semantics must be recovered
separately.

`replay_parked()` returns newly verified tuples without an internal receipt gate.
The outer caller must re-offer them through gate/persistence in the correct
pass; it must not directly treat the tuple as sent.

## Following implementation obligations

A caller component must compose accepted tracker lock/storage, shared operation
clock/context, quote/watch IO, claim verifier, outbox journal and lifecycle gate
with the real bar/live state transitions. It must preserve changed-only order,
separate lock effects, raw bar/quote availability, raw output ordering and the
distinction between queue record, transport delivery and economic trade outcome.
No full causal scheduling/checkpoint claim, historical replay, label generation,
dataset/model readiness or live effect follows from this intake.

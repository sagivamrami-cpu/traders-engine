# Lifecycle outcome and shelf source intake

## Authority and purpose

Authority is retained chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, inspected as text only. The
closed-bar resolver has two dependencies that must remain separate from a
message transition: `_outcome` records a source lifecycle fact and `_shelve`
preserves an expired, unfilled candidate for a later separately revalidated
revival.

This is a prerequisite to resolver recovery, not an outcome-label factory.
Source values such as `tp1`, `expired`, or `stopped_ambiguous` describe a
tracker event; they do not prove fill, P&L, economic success, historical
replay completion, dataset eligibility or model target validity.

## Selected source set

The component projects this tracker-order set and no revival/reader behavior:

```text
OUTCOMES, EXPIRE_H, EXPIRE_BY_STYLE, _outcome, _atomic_json,
has_open, _expire_h, SHELF, SHELF_MAX_H, REVIVAL_COOLDOWN_S, _shelve
```

`OUTCOMES` and `SHELF` become logical chart-desk artifact names. The only
clock adaptation is source `time.time()` to supplied `source.now_epoch()` in
`_outcome` and `_shelve`. Source ordering matters: `_outcome` ensures the
parent exists before obtaining `now`, then appends exactly one JSONL row;
`event_ts=0` intentionally falls back to the operation time because that is
the source truthiness branch. `_shelve` first tolerates absent/bad JSON as an
empty object, preserves `revived_from_ts` over the latest `ts`, stamps one
operation time, then atomically replaces the whole shelf image.

`has_open` remains the accepted tracker-admission behavior and must be
verified as a real child dependency rather than reimplemented. `_expire_h`
must preserve the exact source style/variant priority and constants.

## Effect boundary

The offline source exposes raw artifact operations only: outcome parent
creation/append, shelf existence/text, operation clock, and the already-used
atomic file-handle ports. It may retain controlled test/replay artifacts but
must not open a host path, access a feed/broker, send/deliver a message, infer
a fill, calculate P&L, or emit a training label.

The selected `_atomic_json` cleanup boundary remains source-faithful: only its
inner cleanup unlink is best effort; an original atomic write failure
propagates. No OS-durability or exactly-once claim follows.

## Explicitly deferred

Outcome reading/reconciliation, shelf revival/TTL/cooldown and tree checks,
the closed-bar/live resolver loops, raw corrected-bar and quote causality,
revalidation composition, gate/save integration, execution simulation,
historical replay, dataset construction and all training/evaluation/live
claims remain outside this component.

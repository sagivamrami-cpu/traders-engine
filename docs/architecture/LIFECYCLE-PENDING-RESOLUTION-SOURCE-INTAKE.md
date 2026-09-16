# Lifecycle PENDING-resolution source intake

## Source boundary

The retained chart-desk source is pinned at commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, function
`chartdesk/tracker.py::_check_live_locked`, lines 2619-2646.

This slice begins only after a caller has supplied one active `PENDING` record,
its current price, and the accepted live-resolution evidence map. It ends at
the successful transition to `OPEN` and its fill notice. It deliberately does
not enter the following `if t["state"] == "OPEN"` source block in the same
pass; that composition belongs to the deferred OPEN-resolver slice.

## Required source behavior

1. Derive the entry band and choose `(low, high)` from the supplied forming-bar
   extreme when present, otherwise `(price, price)`.
2. Use the source one-sided touch test: short touches at `high >= zone_low`;
   long touches at `low <= zone_high`. A non-touch makes no change.
3. On a same-symbol, same-direction existing OPEN slot, mark only this pending
   record `CANCELLED`, append the source cancellation message, and write the
   raw tracker fact `open_slot_conflict_at_fill`.
4. Otherwise run accepted `TreeRevalidation.revalidate_pending`. A failed
   revalidation similarly cancels, uses its reason in the source cancellation
   message, and writes `invalidated_at_fill`.
5. A successful revalidation sets `state=OPEN`,
   `revalidation_verified=bool(verified)`, `fill_verification_reason=why or
   "verified"`, and assigns one source operation timestamp to both `filled_ts`
   and `progress_ts`. It appends the accepted source fill message plus its
   revalidation caveat. It does not produce an outcome record merely for a
   fill.

## Composition rules

- Reuse `LifecycleOutcomeShelf.has_open/_outcome`, `LifecycleTransitions`,
  `TreeRevalidation`, and the accepted entry-band helper. Do not duplicate
  their source behavior.
- Adapt only source wall-clock reads to `source.now_epoch()` and `_fmt(symbol)`
  to `symbol.split(":")[-1]`; keep source branch order and raw outcome timing.
- The resolver works only on caller-supplied mappings/prices/extremes. It does
  not load/save state, read quotes/bars, lock, gate/deliver messages, or invoke
  the deferred OPEN branch.
- An outcome row is a raw tracker fact, not a fill assertion, P&L, label,
  replay row, dataset row, or training target.

## Deferred

Outer scan/terminal filtering/price lookup, same-pass OPEN progression,
open-trade protection/progress/targets, caller persistence/gating composition,
causal historical evidence, economic simulation, dataset construction and
model fitting remain deferred.

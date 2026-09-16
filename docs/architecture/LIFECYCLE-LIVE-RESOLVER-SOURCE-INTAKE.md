# Lifecycle live resolver source intake

## Authority and purpose

The retained authority is chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, read and parsed as text only.
This intake recovers the state-resolution kernel of
`chartdesk/tracker.py::_check_live_locked`, from the source evidence block at
lines 2559–2605 through the final per-record OPEN branch at lines 2609–2760.
It deliberately excludes loading, locking, changed-only gate/persist/save and
delivery at lines 2556–2558 and 2761–2764.

The purpose is to compose already accepted PENDING and OPEN projections in the
same physical source order. It is not a new trading policy and it does not
create historical replay, economic labels, dataset rows, training targets or
live-trading authorization.

## Observation interface correction

`LifecycleLiveResolutionEvidence.collect(state)` is an accepted narrow
projection that returns only `(prices, bar_extremes)`. The source's later OPEN
minimum-success branch also needs the one raw quote record from the source
`_q` snapshot. Calling `quote_payload()` again in a composer would create a
third source observation: `_live_prices()` already reads once and the source
block reads `_q` once. That would not be faithful.

The new resolver must therefore own a private, source-audited observation
projection that makes exactly the source observations and returns
`(prices, bar_extremes, raw_quotes)`. It starts with accepted
`LifecycleLiveEvidence._live_prices()` (first quote observation), then reads
the raw quote mapping once with source error-to-empty behavior (second quote
observation), applies the existing active-symbol corrected-bar fallback rules,
and carries the unmodified raw mapping to minimum-success. The earlier narrow
evidence component remains accepted and unchanged; it is not silently widened
or given an incompatible return type.

## Required kernel order

For a supplied mutable state mapping, obtain the private observation snapshot.
If it contains no prices, return `([], False)`. Iterate `list(state.items())`
in source order, skipping terminal records (`STOPPED`, `DONE`, `CANCELLED`) and
records without a price.

For each selected `PENDING` record, call the accepted
`LifecyclePendingResolution` with the full state, spot price and snapshot
forming-bar map. A cancellation stays terminal and continues to the next
record. A successful fill changes the same mutable record to `OPEN` and must
fall through to the OPEN branch in that same source pass.

For an `OPEN` record, invoke components in this exact order:

1. `LifecycleOpenPostfillEvidence.collect(trade, spot)` produces the causal
   post-fill low/high window and provisional bar minimum message.
2. `LifecycleOpenMinimumSuccess.resolve(...)` receives that window, spot, the
   matching `raw_quotes[symbol] or {}`, membership in `bar_extremes`, and the
   provisional message. Its returned message is retained for later suppression.
3. `LifecycleOpenProtection.resolve(...)` runs next. If it changes the trade,
   append its message and continue to the next record; ordinary resolution and
   zone return must not run in that pass.
4. `LifecycleOpenOrdinaryResolution.resolve(...)` runs only after no ambiguity.
   It receives the same window and the actual minimum message. Its ordinary
   target/protective state change is visible on the same mutable record.
5. Only while the record remains `OPEN` after ordinary resolution, invoke
   `LifecycleOpenZoneReturn.resolve(trade, spot=spot)`. This preserves the
   source `else`: no zone message after all targets or protective terminal
   handling.

Accumulate messages in emitted source order and OR the component change flags.
The kernel creates no direct persistence/gate/delivery effect. Raw tracker
facts remain exclusively owned by the already accepted outcome-shelf children.

## Explicit boundaries

The resolver accepts explicit offline ports, including quote snapshots and
corrected-bar access. Its accepted revalidation descendants can retain their
documented corrected-evidence and source-owned shadow-write behavior. This
does not authorize a live feed, broker action, source execution, loading,
locking, gate/persistence, delivery, P&L calculation, replay, dataset
generation, model training, model promotion or live trading.

# Lifecycle closed-bar resolver source usage

`LifecycleClosedResolver(source)` is the pinned offline composition of the
retained tracker `check()` closed-15-minute-bar lifecycle, before caller-owned
gate, persistence, save, or delivery work.

```python
messages, changed = LifecycleClosedResolver(source).resolve(
    tracker_state,
    now=pass_epoch,
)
```

The caller supplies mutable tracker state and a source whose
`fetch_corrected(symbol, "15m", 3)` returns the corrected caller-owned frame
and correction evidence. `now` is the one pass clock for closed-PENDING expiry
and revalidation. Each nonterminal record fetches independently; fetch errors,
unverified correction, `tv_stale` correction, or no bar strictly later than
the plan timestamp skip only that record.

The resolver keeps the two retained extrema windows separate. Post-send closed
bars determine whether a PENDING plan fills; `_open_extremes` supplies only
post-fill extrema to OPEN processing, with exact entry fallback when there is
no position window. Thus a pre-fill target-side high or low cannot pay an OPEN
target after a retest fill.

Successful closed PENDING resolution falls through in the same pass. For OPEN
records the resolver calls `DeskSuccess.observe_bars(trade, since)` directly;
it does not substitute the live-quote minimum component. When that retained
bar observation emits a message, its raw `minimum_success` outcome and source
progress state are recorded before protection. Accepted protection resolves an
unordered protective/target touch conservatively and ends processing for that
record. Otherwise accepted ordinary resolution handles progress, unhit targets
in ordinal order, zero-target completion, and ordinary protective resolution.
The live-only zone-return branch is intentionally absent.

This is not bar acquisition policy, a complete lifecycle caller, persistence,
delivery, fill confirmation, economic result, replay engine, dataset row,
training target, model, or live-trading authorization. Replay and training
readiness remain false.

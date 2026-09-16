# Lifecycle OPEN post-fill evidence usage

`LifecycleOpenPostfillEvidence(source).collect(trade, spot)` is a private,
offline projection of the OPEN post-fill evidence block in the pinned tracker.
It accepts one caller-supplied OPEN record, one already-supplied spot price,
and a source port exposing `fetch_corrected(symbol, "15m", 2)`. It returns:

```python
low, high, minimum_message = collector.collect(open_trade, spot)
```

The returned window starts as `(spot, spot)`. Inside the source's broad tape
guard, the collector obtains the corrected 15-minute tape, rejects an
unverified or `tv_stale` correction unless the accepted
`LifecycleLiveEvidence._historical_replay_safe` predicate permits restored
post-fill history, then locates the fill with the accepted `_fill_on_tape`
helper. Only a located fill permits `_position_extremes(...,
fill_bar_first=True)` to contribute: the tape low/high are combined with spot
using `min(spot, tape_low)` and `max(spot, tape_high)`.

The fill bar is adverse-only for favourable movement. Spot is assumed supplied
as a post-fill observation and remains included on both sides. An unreadable,
unsafe or unlocatable tape leaves `(low, high)` at spot and returns no minimum
message.

The collector invokes `DeskSuccess.observe_bars` on a detached shallow trade
copy solely to recover the source-style `minimum_message`; it never writes the
minimum proof into the caller's supplied record. It does not mutate any
supplied trade, tape or correction object, and does not resolve protection,
targets, progress, state, outcomes, persistence, gates, delivery, economics,
replay, datasets, training, models or readiness.

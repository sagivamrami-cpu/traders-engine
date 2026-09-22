# Lifecycle closed-bar PENDING resolution usage

`LifecycleClosedPendingResolution` is an offline projection of only the
closed-bar `PENDING` branch in the pinned tracker source.  It is deliberately
separate from the live PENDING resolver because the closed-bar branch receives
aggregate 15-minute extrema and has an expiry/missed-move path.

```python
messages, changed = LifecycleClosedPendingResolution(source).resolve(
    trade,
    state=tracker_state,
    since=post_send_closed_bars,
    high=aggregate_high,
    low=aggregate_low,
    now=pass_epoch,
)
```

The caller must supply a verified closed-bar window strictly after the trade
timestamp. `since["open"].iloc[0]` is used only when an untouched plan expires,
to measure the missed directional movement. `high` and `low` are the aggregate
extrema for the same supplied window. `now` is the pass anchor used for expiry
and revalidation; on a successful fill, `filled_ts` and `progress_ts` instead
come from a fresh `source.now_epoch()` reading, matching the source transition.

For a PENDING record the component, in source order:

1. expires an untouched plan after its source style/variant expiry, records raw
   `expired` facts with `missed_r` and `missed_points`, and shelves the record;
2. prevents a second OPEN slot on the same symbol/direction;
3. revalidates a touched plan at the supplied pass clock;
4. records fill verification fields and transitions to `OPEN`;
5. conservatively terminally stops an entry/stop touch in the same aggregate
   window as raw `stopped_ambiguous`; or
6. emits a fill message and returns with `trade["state"] == "OPEN"` so a
   separate, later OPEN resolver may process subsequent behavior.

The shelf and outcome records are raw tracker lifecycle facts. They are not a
fill confirmation, realised P&L, economic label, replay result, dataset row,
or model target.

This component performs no corrected-bar acquisition, quote acquisition,
locking, persistence, gating, delivery, OPEN progression, replay, dataset
construction, training, model inference, or live-trading action. There is no
source-audit or readiness claim in this change.

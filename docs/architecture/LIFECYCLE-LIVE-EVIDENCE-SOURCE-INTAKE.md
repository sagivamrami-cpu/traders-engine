# Lifecycle live-evidence source intake

## Authority and boundary

Authority is retained chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, parsed/read as text only. The
live resolver needs two different evidence decisions before it may resolve a
known state transition: whether a quote is fresh enough to represent *now*,
and whether restored historical bars may represent a post-fill fact after a
collector outage.

## Selected source set

The source-order projection is:

```text
QUOTE_MAX_AGE_S, _live_prices, _historical_replay_safe, FORCE_BAR_AGE_S
```

`QUOTE_MAX_AGE_S=420.0` preserves the existing fresh-quote ceiling. Source
`QUOTES.read_text()` becomes `source.quote_payload()` and source
`time.time()` becomes `source.now_epoch()`. `_live_prices` keeps the source
per-row isolation: bad top-level quote payload becomes `{}`, and a bad quote
row is skipped without losing a good sibling.

`_historical_replay_safe(df, corr, trade)` does not provide a current price and
cannot fill PENDING. It is true only for an OPEN trade, non-empty bars,
non-unverified correction metadata, and a latest bar timestamp at or after
the persisted fill (falling back from `filled_ts` to `ts`). Its limited
purpose is to allow recovery of a timestamped historical stop/TP fact; it
never makes a stale bar a live quote. `FORCE_BAR_AGE_S=120.0` is an exact
constant used later by the resolver’s per-symbol fallback policy.

## Effect and training boundary

The component accepts only raw quote payload, supplied operation clock and
in-memory bar/correction/trade inputs. It does not fetch bars, change state,
send messages, write outcomes, infer execution/P&L, create labels, run replay
or establish dataset/training/model readiness.

## Explicitly deferred

The per-symbol corrected-bar fallback, fill-on-tape/post-fill extremes,
protection/target decisions, zone return, revalidation/gate/save composition,
closed-bar resolver, historical replay, economics, dataset and model work stay
outside this component.

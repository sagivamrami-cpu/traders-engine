# Lifecycle live-resolution evidence source usage

`LifecycleLiveResolutionEvidence(source).collect(state)` is a private, offline
projection of the leading evidence block in the pinned live resolver. It
returns a pair: fresh or corrected `prices` by symbol and winning forming-bar
`bar_extremes` as `(low, high)` pairs.

The collector first reuses the accepted `LifecycleLiveEvidence(source)` quote
filter. For supplied `PENDING` and `OPEN` state records only, a missing or
older-than-120-second fresh quote may be supplemented by
`source.fetch_corrected(symbol, "15m", 2)`. An unverified or `tv_stale`
correction is ignored. A corrected close replaces a quote only when its final
UTC timestamp is strictly newer than the raw quote timestamp; its final low and
high are retained as evidence for a later resolver component.

For fidelity, quote-age conversion and the fresh-quote skip happen before the
per-symbol fallback `try` boundary. Thus a malformed active raw quote timestamp
propagates before any corrected-bar request, while a corrected-bar failure is
contained to that symbol. On a winning corrected bar, `(low, high)` is stored
before its close replaces the price, matching the source order.

All inputs are caller-supplied ports or in-memory objects. The collector does
not load or mutate state, resolve a PENDING or OPEN trade, infer a fill, stop,
target or progress, write an outcome or label, gate/save/deliver, access a
broker/feed, run replay, calculate economics, build a dataset, train a model,
or establish any readiness state. It deliberately does not implement the
source resolver's later empty-price return or any resolver body.

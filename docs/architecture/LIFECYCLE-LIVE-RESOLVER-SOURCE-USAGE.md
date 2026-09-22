# Lifecycle live resolver source usage

`LifecycleLiveResolver(source).resolve(state)` is a private, offline
composition of the pinned tracker live-resolution kernel. It accepts one
caller-supplied mutable tracker mapping and returns source-ordered
`(message, to_group)` tuples plus one aggregate changed flag.

Before scanning, it owns exactly the source's two quote observations: accepted
`LifecycleLiveEvidence._live_prices()` followed by one raw
`source.quote_payload()` snapshot. Its private snapshot returns fresh or
corrected prices, corrected forming-bar `(low, high)` evidence, and the raw
quote map. For active PENDING/OPEN symbols, a missing or older-than-120-second
price can use a strictly newer verified non-`tv_stale` corrected 15-minute bar;
the corrected low/high travel with the winning close. A corrected-bar failure
is isolated to its symbol. The raw quote map is forwarded to minimum-success,
not fetched again.

The resolver scans `list(state.items())`, skips STOPPED/DONE/CANCELLED and
records without a price, and invokes accepted child projections in source
order. A PENDING resolution that fills falls through to OPEN processing in the
same scan. For an OPEN record the order is post-fill evidence,
minimum-success, ambiguity protection, ordinary resolution, then zone return
only while the same record remains OPEN. An ambiguity change appends its
message and continues, so ordinary resolution and zone return do not run in
that pass.

This is an offline, supplied-port composition only. It does not load or save a
tracker, lock, gate, deliver, acquire a live feed, execute a broker action,
calculate economics, run replay, create datasets or training targets, train or
promote a model, or authorize live trading. Accepted descendants retain their
documented effects: in particular, outcome-shelf facts and zone-return's real
revalidation call remain child-owned behavior. The resolver is therefore not
effect-free as a whole merely because it has no direct persistence or delivery
body.

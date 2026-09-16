# Lifecycle live-evidence source usage

`LifecycleLiveEvidence(source)` is a private, offline projection of the
pinned tracker helpers `QUOTE_MAX_AGE_S`, `_live_prices`,
`_historical_replay_safe`, and `FORCE_BAR_AGE_S`.

It accepts exactly two live-evidence ports: `source.quote_payload()` for an
already supplied quote payload and `source.now_epoch()` for the operation
clock. It accepts already supplied in-memory bars, correction metadata, and a
trade record for the historical predicate. It does not fetch a feed, write
state, deliver a message, mutate a trade, select an entry/stop/target, infer a
fill or P&L, create an outcome or label, run replay, or establish dataset,
training, or model readiness.

`_live_prices()` returns only finite, positive quote prices whose timestamp is
within the inclusive `[0, 420]` second age window at the supplied operation
clock. A failing quote payload returns an empty mapping; a malformed row is
skipped without suppressing a valid sibling. It is not a broker or venue quote.

`_historical_replay_safe(df, corr, trade)` is only a narrow fact-recovery gate:
it returns true only for an `OPEN` trade with nonempty bars, no unverified
correction metadata, and a last bar at or after `filled_ts` (falling back to
`ts`). It cannot make a stale quote fresh or turn `PENDING` into `OPEN`.

`FORCE_BAR_AGE_S` remains the source constant (`120.0`) for a later resolver
fallback; this component does not implement that fallback. The companion
source-parity auditor and explicit-root JSON CLI are
`trading_system.tree_spec.lifecycle_live_evidence_source` and
`tools/check_lifecycle_live_evidence_source_parity.py`. They parse the pinned
source, fail closed on source/audit/serialization inconsistency, and retain
both replay and training readiness flags as false. They do not certify replay,
economic labels, datasets, training, models, live resolution, or live trading.

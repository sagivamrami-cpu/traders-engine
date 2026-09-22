# Lifecycle live-resolution evidence source intake

## Authority and boundary

Authority is retained chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, read and parsed as text only.
This intake covers only the leading evidence-acquisition block inside source
`_check_live_locked()`: the source's fresh-price map, per-active-symbol
corrected 15-minute fallback, correction rejection, timestamp comparison and
forming-bar low/high carry-forward.

## Why this is a separate prerequisite

`LifecycleLiveEvidence` already proves whether a raw quote is fresh and
whether a restored bar may describe a post-fill fact. The resolver source then
combines this evidence for each active (`PENDING` or `OPEN`) symbol: a quote
older than `FORCE_BAR_AGE_S`, or absent from the fresh map, may receive a
corrected-bar fallback. The fallback may win only when its last timestamp is
newer than the source quote timestamp. Its close becomes a price and its
forming low/high are preserved separately because subsequent source state
resolution evaluates touches against the range, not only the close.

## Exact recovered behavior

- Start with the accepted `_live_prices()` map and an empty per-symbol
  extremes map.
- Read the raw quote payload again; top-level failure becomes `{}`. Read the
  operation clock. This mirrors the source's two distinct observations.
- Iterate the set of symbols whose supplied state is `PENDING` or `OPEN`.
  Compute source age from raw `ts`; only an existing fresh price with age at
  most `FORCE_BAR_AGE_S` skips fallback.
- Ask the supplied corrected-bar port for exactly `(symbol, "15m", 2)`.
  Skip a candidate whose correction is `unverified` or has source
  `"tv_stale"`, and skip any fallback error without suppressing another
  symbol.
- A corrected bar wins only if there is no fresh price or its final UTC bar
  timestamp is strictly later than `now - quote_age`. On a win, preserve the
  final bar `low` and `high`, and use its `close` as that symbol's current
  resolver price.
- The block makes no state change and decides no fill, stop, target,
  revalidation, outcome, gate, save, delivery, economic result, replay or
  training label. A later resolver-body component alone may consume this
  evidence.

## Deferred

The rest of `_check_live_locked()` — PENDING admission/revalidation/fill,
OPEN post-fill window/location, protection/ambiguity/progress/targets/zone
return, outcome writing and changed-only caller commit — remains deferred.
So do `check_live`, lock acquisition, loading, gating, persistence, delivery,
market acquisition, replay, dataset, training and model readiness.

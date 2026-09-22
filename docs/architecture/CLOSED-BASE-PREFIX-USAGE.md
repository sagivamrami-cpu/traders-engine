# Actual decision time with closed-base price observations

Three existing builders now offer an explicit keyword-only
`closed_base_prefix: bool = False`:

```python
aggregate_daily_asof(bars, period=period, decision_time=T,
                     base_timeframe="5m", session_schedule=calendar,
                     closed_base_prefix=True)
build_frame_asof(frame_spec, decision_time=T, closed_base_prefix=True)
build_levelmap_asof(instrument=symbol, decision_time=T, requests=requests,
                    closed_base_prefix=True)
```

This is an observation policy, not a new trading threshold or implicit default.
Only bool is accepted; numeric0/1 do not masquerade as False/True.

The default retains the previous grid-aligned behavior, validation, versions,
fields and canonical hashes. Prefix mode accepts aware microsecond-exact T
between base closes. Prices end at the UTC-grid floor for the base timeframe,
or the period end if earlier. A bar is still usable only when published by the
actual T. Period/frame metadata and frame freshness are assessed at actual T.
Current daily-period ownership is also based on T; an empty current period must
not inherit yesterday's OHLC. Frame calendar coverage must extend through T.
The direct daily-period aggregator requires coverage through its observation
cutoff, including when evaluating a completed period later.

Example: at00:10:30, a5m bar closed00:10 and published00:10:20 is known. It was
not known at00:10:19. A bar closing00:15 contributes nothing, even if its final
prices are supplied. No availability timestamp is clipped to00:10 to force the
bar through. A freshness budget is measured from actual observation to00:10:30,
not from observation to the floored clock.

| Builder | Prefix schema | Prefix calculation |
| --- | --- | --- |
| Period | daily-period-prefix-asof-v1 | closed-lower-bars-daily-period-prefix-v1 |
| Frame | historical-frame-prefix-asof-v1 | closed-base-frame-prefix-v1 |
| Map | historical-levelmap-prefix-asof-v1 | historical-levelmap-prefix-asof-v1 |

Period/frame results add `observation_cutoff` in prefix mode only, included in
canonical evidence. Available map fetch-frame traces retain that cutoff. The
map snapshot version follows the map calculation version. Prefix and strict
policies deliberately have different hashes even at the same aligned T;
default mode's results remain unchanged.

The map's original session and correction-age gates use actual T; a session can
end without a newer price bar. Snapshot observation/publication remain T and
actual price observation/publication remain in traces. No offsets are applied.
The package-internal `_OfflineSource` accepts the same optional final flag for
the producer adapter; it is not a public caller-supplied feed/readiness interface.

Unknown expected closed history still blocks. Known closures are not holes.
Grid-aligned period boundaries, exact identities, full structural validation,
missing volume and finite arithmetic contracts remain unchanged. Prefix mode
does not invent open-only ticks, partly observed base bars or broker-day labels.
Source calendars/basis/era remain supplied attestations. Readiness stays false.

Verification: `python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=short`.
Tests cover real publication/metadata boundaries, cutoff/clock separation,
forming higher frames, missing/closure/rollover/freshness,23/25h periods, source
session end and future-extension invariance. Captured pre-change fixture hashes
and the original suites protect strict-default compatibility.

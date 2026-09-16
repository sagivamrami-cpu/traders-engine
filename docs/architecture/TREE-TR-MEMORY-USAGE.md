# Original TR vector memory and daily pivot helpers

Private functions in trading_system.tree_replay._vendor.tree_tr:

```python
zones = vector_zones(frame)
zones = vector_zones(frame, supplied_pvsra, zone_from='body',
                     cleared_by='wick', max_zones=500)
pivots = daily_pivots(daily, include_m=True)
```

Component accepted after source audit, tests and independent task/final reviews:
agent-exchange/status/2026-09-09T215229Z-codex-tree-tr-memory.md.
See TREE-TR-MEMORY-SOURCE-CONTRACT.md and plan2026-09-10-tree-tr-memory.md.
No IO, clocks or external data loading here.

vector_zones uses actual accepted default non-auction PVSRA when none supplied.
Only climax candles create zones. Source first-row availability is retained.
Initial overlap does not clear a zone: price must first leave entirely, then
return. Each later overlapping bar after departure counts as a touch. Wick or
body geometry is selected independently for zone and clearing. Nonempty result
has time index and top,bottom,kind,open,touches; source empty result includes an
empty time column instead. Arbitrary supplied frames are not validated or sorted.

The private API omits auction/session_tz parameters; customauction/seasonality
is not supported or certified. Source max_zones slicing remains literal,
including zero/negative semantics. Raw pandas/input errors are not swallowed.

daily_pivots reads the penultimate delivered row; last row is not used. This
does not infer completed daily candles or reconstruct session boundaries.
It returns seven standard pivots and optionally six M midpoints, in source order.

These numerical outputs do not certify causal availability, historical source
coverage, trades or outcomes. Full tree must still assemble the actual readers
and preserve its forming/closed-row conventions and state. No GC/XAU alias,
marketdata acquisition, model fitting or live behavior is enabled.

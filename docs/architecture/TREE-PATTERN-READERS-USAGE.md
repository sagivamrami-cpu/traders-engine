# Original pattern readers (private offline interfaces)

Spec: TREE-PATTERN-READERS-SOURCE-CONTRACT.md. Four instance readers under
trading_system/tree_replay/_vendor preserve the pinned chart-desk calculations:

- WmReader(source).detect(symbol,timeframe='15m') -> Formation or None.
- LiquidityReader(source).pools(symbol,timeframe='15m') -> list[Pool];
  run with the same arguments -> Run.
- BrinksReader(source).today_box(symbol,now=None) -> Box or None.
- ChecklistReader(source).rvc_gvc(symbol,timeframe='15m') -> RvcGvc or None;
  blocks(symbol,timeframe='15m',lookback=60) -> list[Block];
  brinks_read(symbol,timeframe='5m') -> BrinksRead.

Supply fetch_corrected(symbol,timeframe,lookback)->(pandasFrame,correction)
and now_utc()->aware UTC datetime. No production defaults exist. Each call gets
its original request, including LiquidityReader.run's second fetch through
the actual pools reader. ChecklistReader composes the actual BrinksReader;
all vector calculations use real local PVSRA and vector memory, not final
verdicts supplied by a provider. Lookback is a request, not proof of coverage.

These raw ports do not validate causal market history. The caller must supply
what the original reader could observe at the operation time, including its
forming row. RVC and blocks exclude that row as a candidate; ATR/current close
may still consume it. Source catches preserve None/empty results, which must
not be mistaken for proven absence when building features later.

Preserved source quirks: WM and liquidity use different swing priorities and
plateau policies; WM's five-row vector window cannot warm up the ten-row PVSRA
baseline. Brinks uses fixed UTC hours, accepts eight bars, and includes whole-
frame current close. Its formatted range string is not an ISO timestamp;
the actual composed checklist can fail parsing it and report swept_asia=None.
This is documented baseline behavior, not a silently repaired trading rule.
Original numerical thresholds, even those called open parameters by source
comments, remain unchanged. Custom auction behavior is not implemented.

Source/runtime reviews and component acceptance completed; see
agent-exchange/status/2026-09-09T220345Z-codex-pattern-readers.md. No whole tree,
causal replay, entry fill, economic label, dataset, model or live readiness is
implied. Next work remains the options reader, full walk/builder/caller binding,
remaining producers and economic simulation.

# Original tree walk over raw offline ports

Status: component accepted after task/final reviews, 293 combined passing tests
and a fresh full source-graph audit. Evidence:
agent-exchange/status/2026-09-10T193848Z-codex-tree-walk.md.
Authority: TREE-WALK-READER-CONTRACT.md, pinned chartdesk/tree.py. This is a
private offline composition, not a public causal replay or trained model.

`TreeReader(source).walk(symbol, variant='house')` runs all twelve original
visited stages. `strict` additionally appends the thirteen previous-day pivots.
`walk.complete` means TARGET with no stop reason, not that every observation
was positive. Missing observations and negative findings remain distinct.

The reader constructs actual basis/map/stretch/pattern/liquidity/options readers
and uses the actual matrix, EMA/cloud, PVSRA, vector-memory and calendar logic.
No final Walk, map, pattern, matrix or Plan verdict is supplied by the provider.

Required raw ports:

- `fetch_corrected(symbol, timeframe, lookback)` returns a pandas OHLCV frame
  and the source-compatible correction object (or raises the actual read error).
- `now_utc()` returns an aware UTC operation time, separately on each call.
- `calendar_text('news-desk/data/ff_calendar.json')` returns raw calendar JSON.
- `list_reports()`, `read_report(logical_id)`, `read_tv_csv(filename)` supply
  the original options-reader raw artifacts. Failures retain original catches.

Repeated keys can return different available snapshots. Do not cache all reads
under one pass timestamp: news captures time before reading its calendar; session,
Brinks and provisional PSY have separate clocks. Construction performs no IO.
The original requested lookback is not permission to trim all delivered history.
Original forming/completed-row conventions are retained, not normalized away.

`first_vector_above_50(symbol, timeframe='5m')` returns the source setup dict
or None. It reads the completed candle and the preceding six closes against
the actual EMA50 cloud; a setup is not an order.

`trade_from_walk(w)` rereads current 15m prices and the map, applies strict
greater-than .33 ATR decision drift, incorporates vector midpoints within
5 ATR, and uses original intraday stop bands and named distinct targets.
It returns the original pricing Plan or None. Some geometry/R:R refusals keep
the actual rejected Plan in `w.refused`; unavailable inputs are not economic
loss labels. `levels_to_trade(symbol, close, direction, atr, variant='house')`
is the separate original geometry consumer: returns `(stop, targets)` or None,
and raises LevelsUnavailable for an unreadable universe.

Plan.tradeable is internal source pricing acceptance only: outer admission,
cross-producer arbitration, fills, costs, exits and measured outcomes are still
separate. No new win rate, outcome-learning dataset or model is produced here.

Runtime verification:

```powershell
python -B -m pytest tests/tree_replay/test_tree_walk.py tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_pattern_readers.py tests/tree_replay/test_optionswall.py tests/tree_replay/test_tree_tr.py -q --tb=short -p no:cacheprovider
```

Fixtures supply raw synthetic tapes and hand-derived expected decisions/prices.
They are not historical feed/publication certification. Full source projection
audit and component review gates passed; causal providers and the market-watch
caller remain before real replay. The actual reader must next bind
Revalidation.tree_walk; that existing raw port is not currently a complete tree
integration. Run the source audit with an explicit parent of retained checkouts:

```powershell
python -B tools/check_tree_walk_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

VERIFIED certifies these source projections/dependencies only, not replay or
training readiness. Missing source authority returns a blocked report, including
the known missing-baseline-pin failure from the inherited EMA audit.

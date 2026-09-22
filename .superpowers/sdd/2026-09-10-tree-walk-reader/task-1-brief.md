# Task1 requirements

## Global constraints

- Existing approved feature checkout; main inline critical path and independent
  review sidecars. No nestedagents/commits/cleanup/unrelated changes.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, tree.py
  fdb439a39bbd35230e421c0319c6be0e2fbfbc1d. Original source read/parse only.
- No rewritten rules, provider-final Walk/Plan/map/pattern/matrix values,
  default readiness, new thresholds, economic labels, data or live actions.
- House/strict, original missing/negative/error distinctions, separate clocks,
  full source bodies and actual dependencies required. Fixed-T APIs unchanged.

## Task1: Complete raw-port tree and geometry

Create trading_system/tree_replay/_vendor/tree_core.py, tree_signals.py and
tree_walk.py, tests/tree_replay/test_tree_walk.py and
docs/architecture/TREE-WALK-READER-USAGE.md.
Interfaces: TreeReader(source).walk(symbol,variant='house')->original Walk;
first_vector_above_50(symbol,timeframe='5m'); levels_to_trade(symbol,close,
direction,atr,variant='house'); trade_from_walk(w)->original Plan or None.
Original _variant_levels and _trend_ladder are methods; pure helpers are core.

- [ ] Write lazy-module RED tests. RawSource records exact fetch key, raw artifact
  reads and each operation clock; optional failures are raw exceptions. First
  literal case proves DATA stop, without mocking any derived answer:
  ```python
  source = RawSource(frames={})
  w = api().TreeReader(source).walk('OANDA:XAUUSD')
  assert w.reached == 'DATA' and not w.complete
  assert w.stopped_because == 'אין נתונים (LookupError)'
  assert source.calls == [('fetch','OANDA:XAUUSD','15m',10)]
  ```
  Add raw failing4h/unverified15m/unverified4h/stale/min5rows; pure trap_direction
  table across both edges/all4vectorcolors/SV/no-side; stoppingvolume body.35,
  wick.5, volume1.5/equality, missingvolume and completed-vs-forming row.
- [ ] Build raw multi-frame fixtures with pandas OHLCV, not derived ToolReads.
  Rising close series `100+i/100` with open=close-.005, high=close+1,
  low=close-1, volume100 and1000rows yields a positive ordered EMAfan. Supply
  exact keys used by DATA/ladder and full map fixture from operation-map tests
  (read its literal recipe, no implementation-derived expected output). Calendar
  text is JSON containing a low-impact event one day AFTER fixed testclock.
  Optional report list is empty, TV read raisesFileNotFoundError. Assert actual
  full12stage Walk, direction/stamp and facts/missing; ordinary volume is not SV
  and a <.15ATR completed move is a recorded negative, not a hard veto.
  Include neutral/mixed timeframe fixtures, actual map/strict13pivots, unusable
  news/no future coverage/inclusive15min/missing impact; separate clocks and
  original fetch order. Brinks/WM/RVC and vector memory use actual raw fixtures.
- [ ] Test FirstVector with >=100flat128closes then completed high-volume break,
  final forming row not used for vector decision. Both sides; full cloud edge,
  six preceding closes, boundary equality/shortframe/unverified/missingvolume.
  Test builder with original complete Walk, raw15m+actual map: priced and
  refused cases, both directions, original distinct targets/obstacles, vector
  midpoint anchor within5ATR, strictdrift>.33, map reread failure and stop clamp
  refusing when invalidation no longer survives. Assert source Plan properties,
  not fills/profit labels; verify two geometry consumers' separate refusals.
- [ ] Run `python -B -m pytest tests/tree_replay/test_tree_walk.py -q --tb=short -p no:cacheprovider`.
  Confirm normal missing-module assertions before production files exist.
- [ ] Inertly extract whole source into core+reader, preserving all nodes once.
  Use AST transformation to retain docstring values exactly:
  ```python
  methods = {'_variant_levels','_trend_ladder','walk',
             'first_vector_above_50','levels_to_trade','trade_from_walk'}
  # Each selected function gets self; every other non-import node goes to core
  # in original order, including both FINAL_STAGE assignments. No source exec.
  node.args.args.insert(0, ast.arg(arg='self'))
  ```
  Use only enumerated source substitutions from spec, checked once per site;
  explicit core imports and actual reader construction. Numerical dependencies
  imported, not copied/reimplemented. All local edits via apply_patch.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_tree_walk.py tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_pattern_readers.py tests/tree_replay/test_optionswall.py tests/tree_replay/test_tree_tr.py -q --tb=short -p no:cacheprovider`.
  Document raw-port/UNADMITTED limitations, full diff/hashes/report, independent
  task spec/quality review; resolve findings before component acceptance.

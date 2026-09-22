# Task1 brief

## Global constraints


- Approved feature checkout, main inline criticalpath, independent review
  sidecars; no nestedagents, commits, cleanup, unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; exact four blobs in spec.
- Read/parse retainedsource only. No live/data/labels/models. No policychanges,
  invented thresholds, defaultfeed or claims of causal/fulltree readiness.
- ActualWm/Liquidity/Brinks/Checklist and actualPVSRA/vector_zones required;
  do not replace composedreaders by finalverdict providers.
- tree-tr-memory component acceptance required before dependent acceptance,
  not before disjoint runtime/audit implementation.


## Task1: Complete original readers and behavioral integration

Create trading_system/tree_replay/_vendor/{wm,liquidity,brinks,checklists,pattern_tr}.py,
tests/tree_replay/test_pattern_readers.py,
docs/architecture/TREE-PATTERN-READERS-USAGE.md.
Actual files are individual names, not a shell brace-expanded write command.
Consumes fetch_corrected(symbol,timeframe,lookback), now_utc() suppliedports.
Produces WmReader.detect, LiquidityReader.pools/run, BrinksReader.today_box,
ChecklistReader.rvc_gvc/blocks/brinks_read, all original defaultarguments plusself.

- [ ] Write lazyapi missingmoduleRED tests. Build rawframeprovider recording
  each exact request and raising capturederrors; explicit UTC clockcounter.
  Use actual numericaldependencies and literal fixtures, no finalverdictmocks.
  ```python
  # W fixture: interpolate closes over these anchors, OHLC close +/-1,
  # open=close, volume1;40rows. Leg lows89,90; neckline111; finalclose115.
  anchors={0:100.,5:103.,10:90.,17:110.,25:91.,35:115.,39:115.}
  f=make_frame_from_anchors(anchors,40)
  p=Frames({('X','1h',10):f})
  got=api('wm').WmReader(p).detect('X','1h')
  assert (got.kind,got.leg1,got.leg2,got.neckline,got.confirmed)==('W',89.,90.,111.,True)
  ```
  Implement test helpers locally: make_frame_from_anchors creates np.interp
  closes and pd.DataFrame(open=close,high=close+1,low=close-1,close,volume=1)
  over UTC5minindex; Frames exactkeymapping returns(frame,None), detachesframes,
  supports correction/failure overrides and captures calls.
- [ ] Add tests for WM mirroredM, confirmedcloseboundary, plateau dedup,
  newestselection/age/tolerance, <30/proxy/error,5rowPVSRA unearnedtattoo.
  Pure_swings tests show WMlowpriority and liquidityhighpriority on flatbar.
  Liquiditypools fixture interpolate equalhighs at10and25, thenretreat; literal
  two touches/newestage/price and strictsweep. Run needs recentrange>=1.5ATR
  and sweptpool; use realpools secondread and explicitly differing replies.
  Test no run on speedalone, short/equalclose, min40/tail120/pricegrouping.
- [ ] Add Brinks clock/window cases14:59:59/15:00/19:59:59/20:00,weekday/weekend,
  explicitnow bypassclock; frame containing8rows14:00..14:35 producesbox,
  7rowsNone;15:00rowexcludedfrombox butwholeframeclose retained. Actualvector
  memory orNoneoncapturedinputerror; midpoint and originalrangeformattedstamp.
  Checklist Brinks actualreader thenzones, insideboundaryinclusive, rawformed_at
  parsing=>sweptNone; separate rawfetchfailures retainNone notemptylist.
- [ ] Add realPVSRA RVC/GVC rows:30ordinaryhistory, redvol3 then greenvol10,
  finalformingrow deliberatelyopposite; lasttwocompleted used, inclusivebody
  recovery, secondwickratio2boundary andzerowickfalse. Mirrordirection.
  Blocks body.60/.45 thresholds, size1ATR, min40, excludesforming, newestorder,
  suppressedpoorquality and actualkindfilter; retain source exceptions.
- [ ] Run normalRED:
  `python -B -m pytest tests/tree_replay/test_pattern_readers.py -q --tb=short -p no:cacheprovider`.
- [ ] Inertly transform complete original modules, retaining allnonimportnodes
  inoriginalorder except listedmethods moved to newclass. Exact imports and
  substitutions in spec; inspect originals/ASTcounts and fullgeneratedoutputs.
  ```python
  class ChecklistReader:
      def __init__(self,source):
          self.source=source
          self.brinks=BrinksReader(source)
  # onefetch substitution per listedmethod; run pools->self.pools;
  # today_box clock->self.source.now_utc; brinks_read->_actual BrinksReader.
  ```
- [ ] GREEN:
  `python -B -m pytest tests/tree_replay/test_pattern_readers.py tests/tree_replay/test_tree_tr.py tests/tree_replay/test_reversal.py -q --tb=short -p no:cacheprovider`.
  Document exact ports/rawlimitations and capturedsourcequirks; package7files
  for independenttask spec/quality review. No fulltree/caller claim.



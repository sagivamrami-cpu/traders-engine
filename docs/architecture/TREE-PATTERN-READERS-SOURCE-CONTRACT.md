# Original tree pattern, liquidity and Brinks readers

Approved source-faithful master C/D continuation. Main read complete source
files while preparing FULL-TREE-WALK-SOURCE-INTAKE.md. No new trading design or
thresholds. Four private readers share supplied raw frame/correction and clock
ports; calculations are original, not provider-supplied verdicts. Separate
options bridge/fulltree/caller/causalprovider work remains mandatory.

## Authority and projection

chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:
- wm.py d04a462eb0692ed991f25ea2633d8c81783db877
- liquidity.py d73f06f323d39142932cb218935c15455244ce8b
- brinks.py 5c69c3367221e818a2b82f3ca559e1c5a36af675
- checklists.py 5c78955a6bb58d88c8117274606409fced65e22c

Source text/AST only; no retainedsource execution. Whole module executable
nodes retained except top imports and moving selected source functions into
reader classes. Preserve original docstrings, annotations, catches, dataclasses,
constants (including Tuple assignments), helpers and their relative order.
No simplification of names/messages/thresholds or merging divergent swing logic.

New private pattern_tr.py is exactly these actual dependency reexports:
`from .pvsra import pvsra` and `from .tree_tr import vector_zones`.
It is checked as a whole shim, and both dependency audits are mandatory.

Every reader __init__(source) stores self.source. ChecklistReader also stores
self.brinks=BrinksReader(source). Pure nodes follow originalsourceorder;
reader class comes last. Methods stay in original relativeorder and gain self
as firstpositionalargument only. Original topimports preserved except basis
removed, tr becomes pattern_tr as tr, sessions becomes map_sessions as sessions;
checklists adds from .brinks import BrinksReader. No unused live dependency.

| Runtime file/class | Original methods | Exact boundary changes |
| --- | --- | --- |
| wm.py/WmReader | detect | one basis.fetch_corrected(symbol,timeframe,10) -> self.source.fetch_corrected |
| liquidity.py/LiquidityReader | pools,run | one samefetch in each; run's pools(symbol,timeframe) -> self.pools once |
| brinks.py/BrinksReader | today_box | one fetch(symbol,'5m',2) -> self.source.fetch_corrected; datetime.now(timezone.utc) -> self.source.now_utc once |
| checklists.py/ChecklistReader | rvc_gvc,blocks,brinks_read | fetchTF5 once inrvc;fetchTF10 once inblocks;fetchTF10 and15m3 eachonce inbrinks_read; remove local from . import brinks as _bx; _bx.today_box(symbol) -> self.brinks.today_box(symbol) once |

Original method bodies otherwise unchanged. Source signatures/decorators/order
and literal substitutioncounts must be audited independently from candidate.
No method reads provider-finalFormation/Pool/Box/RvcGvc/BrinksRead values.
Source contract fetch_corrected(symbol,timeframe,lookback)->(frame,correction)
and now_utc()->datetime; no live defaults or inferredhistoricalclock.

## Behavioral requirements

WM: SWING_K3; lows checked beforehighs, plateaus dedupgap<=k/valuegap<1e-9,
last plateauindex retained. detectTF10/min30; correctionunverified/initialerror
None. ATR includes deliveredlastrow; lasttwolegs, interveningoppositepivot,
tolerance.5ATR/minheight.8ATR/maxage40. Strictclose pastneck confirms; fresherM
beatsW, equalagekeepsW. vec_near local5rowPVSRA is real; do not claim unavailable
warmup as measuredtattoo. Rawpostfetchcalculationerrors remain original.

Liquidity: highs checked beforelows, noWMplateaudedup. poolsTF10/min40,
tail120, tolerance.25ATR, groupagainstfirstprice (not driftingcentroid), used
members retained, meanprice/newesttouch, strictbeyondlevel+/-tol sweep after
newesttouch, stable sort newestfirst. runTF10 again, completed[-5:-1] bars,
coveredrange>=1.5ATR; then actualself.pools rereads TF10. Mustfind sweptpool
withpriceinside recentrange; speedalonefalse. Direction close>firstopen else
short; original canretain a different-sidepool. No source-policy repair.

Brinks: supplied now or operation nowUTC; weekdays15<=hour<20. Fetch5m2,
unverified/error/emptyNone; same-day14<=time<15UTC selection, min8rows (not12),
boxhigh/low and currentclose from wholeframe. ActualPVSRA(seg)+vector_zones(seg,pv)
gives count or unavailableNone; not0onerror. formed_at exactsource range text.
Midpoint comparison/rendering unchanged including equalmidpoint wording.

Checklists: rvcTF5/min30, two completedrows[-3,-2], bothvectortiers, red->green
RVC long andgreen->redGVCshort, closebodyrecoveryinclusive, secondwicks ratio<=2
onlyifsmallwick>1e-9. BlocksTF10/min40, fullframeATR, excludes forminglastrow,
kindfilter, goodbody>=.60/range>=1ATR, borderline>=.45, sortnewestfirst.
BrinksRead actualBrinksReader plusTF10 vectorzones: onlyopenmidpoints inclusive
insidebox; absentvsunknownlistsdistinct. Asia15m3, midnight<=hour<7 dayderived
from pd.Timestamp(box.formed_at).tz_convert('UTC'); source rangeformattedstamp
canfail and yield swept=None. Retain that behavior and document, no silentfix.

## Validation and limits

NormalRED then actual original runtime; tests use supplied rawOHLCV/correction,
literal expectedgeometry/classifications and requestorder. No final-reader mocks
for primarytests. WM literal pivotfixtures, bothdirections andtie; liquidity
actualgroup/run and reread; Brinks exactclock/window and rawtimestamp failure;
RVC/blocks actualPVSRA with volumehistory. Sourceproof wholemodule/independent
literalpins/identity/mutations and actual tree_tr/PVSRA audits; CLI explicitly
parentroot, JSON0/2, runtime/source importguard, readinessalwaysfalse.

Independenttask/finalreviews before acceptance. Do not modify originaltrading
or accepted EMA/map/revalidation interfaces. No commits/cleanup/data/models/live.
Rawframes notcausalcertification; sourcecaughtNone/[] notknownnegative feedfacts.

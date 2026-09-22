# Original level map and broker-shape operation clocks

Approved master C/D continuation. Source intake:
LEVELMAP-OPERATION-CLOCK-SOURCE-INTAKE.md. Main read complete selected source
functions and accepted fixed-T implementations. Keep public fixed-T interfaces
and their original audits unchanged; this additive private path serves fulltree.

Authority chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:
levelmap.py01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e;
basis.pyf3396f3a9fefd71f0f71422001a5521af0a05cd2.
Only read/parse source. Existingfeaturecheckout, inline implementation plus
independentreviews, no commits/cleanup/data/models/live/unrelatedchanges.

## Architecture

Raw source supplies fetch_corrected(symbol,timeframe,lookback)->(frame,corr)
and now_utc()->aware UTC datetime/Timestamp. It does NOT supply final levels
or broker-shape verdicts. New private BasisOperation(source) forwards raw fetch
and now calls and calculates the actual original broker_shape_ok. This small
shared facade allows other original readers to use the same real predicate later.
No cache, coercion, normalization or exception catch added by forwarding.

LevelmapOperation(source) constructs self.source=BasisOperation(source), and
contains original _session_open_levels(symbol,missing=None,now=None) and
build(symbol,missing=None), with self added first. Source range/session/EMA/
quarter/backday functions and NamedLevel remain actual accepted dependencies.
Reuse _ema_levels from levelmap_build; do not copy it or accept final EMAlevels.
Both operation methods keep complete source bodies. Existing build_at remains
the supported fixed-T public pathway, no globalpatch/injectedcallable tricks.

Some build body overlaps the accepted fixed-T source projection. This explicit
separate source variant keeps both interfaces and source proofs stable; its
whole original AST is independently checked. Do not refactor source branches
into guessed shared logic or alter existingpublic APIs to avoid that overlap.

Review disposition I1 (2026-09-10): this deliberate duplication remains a
maintenance obligation at source upgrades. The operation audit must invoke the
existing full fixed-T graph audit, so changing either body alone invalidates
certification. It is not permission to maintain unverified divergent policies.
Docstrings retain their original literal values even when moved into a class.

## Exact projection

basis_operation.py imports pandas, EXCHANGE_NATIVE from .correction, and contains
only BasisOperation with constructor/self.source, forward fetch_corrected and
now_utc, then original broker_shape_ok(corr,days:float)->bool plusself. Replace
one pd.Timestamp.now('UTC') with pd.Timestamp(self.source.now_utc()). All original
branches and annotations retained. No clock read on None/purebroker/exchange-
native/nonspliced paths; a splice withtv_from reads once at actual operation.

levelmap_operation.py imports futureannotations, pandas, actual .map_tr as tr,
.quarters, .map_sessions as sessions, .back_days._back_day_levels,
.levelmap_build.NamedLevel/SESSION_OPEN_LEVELS/_ema_levels, .basis_operation.BasisOperation.
No sourceNamedLevel copy. Reader constructor above, then source _session_open_levels
andbuild in originalorder with self first. Inject basis=self.source immediately
after eachdocstring. In sessionhelper replace exactly pd.Timestamp.now('UTC')
with pd.Timestamp(self.source.now_utc()); explicitnow conditional remains intact.
Inbuild replace exactly _session_open_levels(symbol,missing) with
self._session_open_levels(symbol,missing), and _ema_levels(symbol,missing) with
_ema_levels(symbol,missing,source=self.source). No other statementchanges.

Original sourceimports and selectedsignatures/decorators/order verified before
projection. Basis originalEXCHANGE_NATIVE and reused levelmapnodes verified by
real inherited check_levelmap_source_parity.check_source_parity(chartdeskroot),
which includes correction/range/pricing/strictEMA/session/backday closures.

## Required behavior

Sessionclock comes after fetch5m3 and successful nonempty/correction checks.
No clock on earlyreturns; explicitnow bypasses onlyclock, notfetch. Openingbar
selection is exact, firstduplicate; source-null andsource-none reject. Spliced
openingbar mustbeat/aftertv_from even when shape qualifies. VenueDST/weekdays/
startinclusive/endexclusive preserved. Errors after original fetchcatch remain.

Fullbuild actual1d400/ranges/backdays, sessionfetch/clock, PSYpreferred1h20 then
15m20 asoriginal, EMA1h240/4h240, quarters order; broker clocks occur only at
source splicepredicate sites. Source families preserve differing gates, missing
lines, returns and typeidentity. No pivots inserted into this map. Actualfull
build test uses hand-derived daily/session/psy/EMA/quarter values, not mapmocks.

Frame reads may advance suppliedclock; lateroperations see neweroperationtime,
but do not retroactively replace earlier frames. This layer does not establish
artifactpublication or scheduled acquisition evidence. Do not backdate a map
to the start of a pass. Operationorder proof is not historicaldata certification.

## Acceptance

NormalmissingmoduleRED, literal rawframe fixtures and real dependencies. Clock-
boundary duringfetch, noextraearlyclock, explicitnow, splice20/7day boundaries,
nativeBTCno-clock, exactsessionbar and fullbuildorder covered. Existing fixed-T
map suites remain green. Source audit independently pinsbothfiles/imports/
signatures/selectednodes/constructor/forwarders/substitutioncounts and actual
graphdependency; errors/drift block, false readinessalways. CLI --source-root
explicitparentroot JSON0/2/unrelatedcwd/importguard. Runtime mutations moving
clockearly or droppingactualbrokerpredicate mustfail literaltests.

Task/final independent reviews required. This is not fulltree/caller/lifecycle/
simulator/dataset/model completion. Next actualtreewalk/builder and revalidation
composition, then completecausalproviders andremainingmaster obligations.

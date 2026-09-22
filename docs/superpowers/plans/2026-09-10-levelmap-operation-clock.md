# Level map operation clock implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Preserve original map and broker-shape operation clocks for fulltree.
**Architecture:** Actual BasisOperation predicate plus LevelmapOperation reader
over rawframe/clock ports; reused accepted numericalgraph. Fixed-T APIs unchanged.
**Tech Stack:** Python/pandas/AST/pytest.
**Spec:** docs/architecture/LEVELMAP-OPERATION-CLOCK-CONTRACT.md

## Global constraints

- Existingapprovedfeaturecheckout, maininlinecriticalpath, independentreview
  sidecars. No nestedagents/commits/cleanup/unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; levelmap.py
  01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e, basis.pyf3396f3a9fefd71f0f71422001a5521af0a05cd2.
- Source read/parseonly; no live/data/labels/models. No newthresholds or final
  level/broker-verdict providers. Existingfixed-Tlevelmappublic APIs unchanged.
- Raw fetch_corrected(symbol,timeframe,lookback) and now_utc() only. Actual
  basispredicate and accepted ranges/EMA/sessions/quarters/backdays required.

## Task1: Original operation-clock readers

Create trading_system/tree_replay/_vendor/basis_operation.py,
trading_system/tree_replay/_vendor/levelmap_operation.py,
tests/tree_replay/test_levelmap_operation.py,
docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md.
Interfaces: BasisOperation(source).fetch_corrected/now_utc/broker_shape_ok;
LevelmapOperation(source)._session_open_levels(symbol,missing=None,now=None)
and build(symbol,missing=None). Output actualNamedLevel/correction.

- [x] Write lazyapi normalRED, rawsource fixture with currentclock and a
  per-fetch aftertime; actualCorrection and literal OHLC/pandasframes.
  ```python
  # London summer opens07:00UTC. Clockbeforefetch06:59:59, afterfetch07:00.
  # opening row07:00 open103/high110/low90/close100; genuine tv_daily.
  levels=api().LevelmapOperation(source)._session_open_levels('OANDA:XAUUSD')
  assert [(x.name,x.price) for x in levels]==[('LONDON-OPEN',103.)]
  assert source.calls==[('fetch','OANDA:XAUUSD','5m',3),('clock',)]
  ```
  Endexclusive London15:30UTC/NY20:00UTC, winterUTCshift, missingexactbar,
  firstduplicate, spliceseam equality versuslater, weekends, explicitnowbypass,
  None/empty/source-none/error earlyreturns with noclock. Keep rawexceptions.
- [x] Test actual broker_shape_ok: Nonefalse/noclock, tv_daily/mt5true/noclock,
  BTCexchange exemptionbeforeclock, othersfalse/noclock, splicecorrect20/7day
  equality andjustshort boundaries from actual nowport. No readyverdict mocks.
- [x] Wholebuild fixture:220daily rows at100/110/90/100 exceptlatest
  100/115/95/110;07:00/13:30 opens103/107; forexPSY33hourrows endingSep7
  06:00UTC high150/low80;1600hour+400fourhourconstant100 EMAframes. Reuse
  literalfamilyexpectedvalues from tests/tree_replay/test_levelmap_source.py
  after reading it; not its implementation to compute expected outputs.
  Assert actual levels/kinds/missing and readorder including lateclock;
  dailyfetchfailure stops before anylaterport, PSYfallback and unequalfamilygates.
- [x] RED `python -B -m pytest tests/tree_replay/test_levelmap_operation.py -q --tb=short -p no:cacheprovider`.
- [x] Inertly project original predicate and2mapmethods; exactsignatures and
  docstring-preserving self/basisbindings, substitutions per spec. Constructor:
  ```python
  class LevelmapOperation:
      def __init__(self,source):
          self.source=BasisOperation(source)
  # Session clock replacement ONLY where original pd.Timestamp.now occurs.
  _replace_exact(node,"pd.Timestamp.now('UTC')",'pd.Timestamp(self.source.now_utc())')
  ```
  Actual imported NamedLevel/SESSION_OPEN_LEVELS/_ema_levels/mapdependencies;
  forwardingmethods have no catches/cache. apply_patch only, inspectfulloutputs.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_levelmap.py tests/tree_replay/test_levelmap_source.py tests/tree_replay/test_correction_source.py -q --tb=short -p no:cacheprovider`.
  Documentinterfaces/clocklimits, package4files and task spec/qualityreview.

## Task2: Whole operationgraph source proof

Create trading_system/tree_spec/levelmap_operation_source.py,
tools/check_levelmap_operation_source_parity.py,
tests/tree_spec/test_levelmap_operation_source.py.
Interface audit_levelmap_operation_source(parentroot) -> report.

- [x] Missing-auditorRED and literalverified/no-readiness fixture:
  ```python
  r=api().audit_levelmap_operation_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Mutate bothruntimes/earlyclock/sessionboundaries/helperbinding/brokershape/
  constructor/forwarders/imports/signature; sourceidentity/blob/order/duplicate/
  count/missing/syntax and actual reuseddependencies mustblock. Dependency
  falseempty/error/trueblocked propagation, CLI unrelatedcwd/importguard.
- [x] RED `python -B -m pytest tests/tree_spec/test_levelmap_operation_source.py -q --tb=short -p no:cacheprovider`.
  Then independentliteralpins/imports/signatures/constructors/forwarders,
  sourceorderedselection andexactsubstitutions, fullorderedcandidatecomparison.
  Actual tools.check_levelmap_source_parity.check_source_parity(parent/'chart-desk')
  mandatory with allblockers preserved. Required --source-root CLI JSON0/2.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_spec/test_levelmap_operation_source.py tests/tree_replay/test_levelmap.py tests/tree_replay/test_levelmap_source.py tests/tree_replay/test_correction_source.py -q --tb=short -p no:cacheprovider`;
  standaloneCLIexplicitparent. Candidate-only clockordering/brokerpredicate
  mutations mustfailruntimefixtures; recordterminalresults/hashes.
- [x] Package3files, task/finalreviews, resolvefindings and acceptance record;
  updateusage/AGENTS/master/tracker. Keep allremainingmasterwork explicitlyopen.

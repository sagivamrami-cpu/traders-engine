# Original options wall reader implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Supply original options context through raw offline artifacts.
**Architecture:** One instance reader retaining actual parsing/mapping/expiry;
independent fullsource audit. Final Walls are outputs, never providerinputs.
**Tech Stack:** Python/pandas/json/AST/pytest.
**Spec:** docs/architecture/OPTIONS-WALL-READER-SOURCE-CONTRACT.md

## Global constraints

- Approved featurecheckout; main inline criticalpath, independent review
  sidecars. No nestedagents/commits/cleanup/unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
  optionswall.pyc7d27ca396c162f6997b2a72bbd035ed6477e05b. Source read/parse only.
- Original numerical/exception/order semantics, no newthresholds/defaultIO/
  livefeeds/GCspotmapping. No labels/dataacquisition/model/liveapproval.
- Source ports list_reports(), read_report(id), read_tv_csv(filename), now_utc();
  raw text/operationclock only. Actual json/pandas and source helpers required.

## Task1: Actual artifact reader

Create trading_system/tree_replay/_vendor/optionswall.py,
tests/tree_replay/test_optionswall.py,
docs/architecture/OPTIONS-WALL-READER-USAGE.md.
Interface OptionsWallReader(source).status(symbol,_current_spot=None,*,now=None),
load(symbol,spot); _anchor(symbol,market_asof) internally composed.

- [x] Write lazyapi normalRED and rawartifact fixtures. Literal report:
  ```python
  entry=dict(symbol='GLD',data_asof='2026-09-09T15:00:00Z',
      quote_permission='realtime_permission',spot=200,
      expiries=[dict(expiry='2026-09-09',walls=dict(
          call_walls=[dict(strike=210)],put_walls=[dict(strike=190)]),max_pain=205)],
      gex=dict(regime='long_gamma',flip_level=201,
          largest_positive=dict(strike=215),largest_negative=dict(strike=185)))
  # raw JSON json.dumps({'symbols':[entry]}), CSV
  csv='time,close,src\n2026-09-09T14:45:00Z,2000,OANDA:XAUUSD\n'
  # supplied clock15:30Z, actual ratio10; call2100/put1900/flip2010/maxpain2050
  r=api().OptionsWallReader(source).status('OANDA:XAUUSD',99999)
  assert r.usable and r.walls.call_wall==2100 and r.walls.ratio==10
  ```
  RawArtifacts helper logsports and holdsunsortedlogicalIDs/rawtext/exceptions;
  no finalWalls or parsedDataFrame mocks. Exercise allsourcefailure reasons,
  lexical latest/no fallback, firstundegradedETF, unsupportedbeforeports,
  malformedJSON/caughtOSError and originaluncaughterrors.
- [x] Add age[-2,45]andoutside, explicitnowbypass/naiveUTC, CSVfutureexcluded,
  anchor75inclusive/75+epsilon, srcpresent/absent, latestbadprice/no fallback,
  NYexpirydate andfirstinputorderexpiry. FirstOIwallmissing/nonfinite, optional
  zero/None, underlyingzero/negative, allsupportedmappings/noGC, loadcomposition,
  currentpriceinvariance. Literalexpectations and exactoperationcallorder.
- [x] `python -B -m pytest tests/tree_replay/test_optionswall.py -q --tb=short -p no:cacheprovider` normalRED.
- [x] Parse source inertly, verify exactliteralimports/inventory/signatures,
  move3methods and addself; applyspec's7exactonceexpression substitutions.
  ```python
  _replace_exact(node,'_anchor(symbol, market_asof)','self._anchor(symbol, market_asof)')
  # Use the spec's full method-specific table; no retainedsource execution.
  ```
  Remove only2physicalglobals/3imports, addStringIO, preserve everyothernode.
  apply_patch only; main read generatedmodule.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_optionswall.py tests/tree_replay/test_pattern_readers.py -q --tb=short -p no:cacheprovider`;
  documentrawports/limits, package3files and independenttask spec/qualityreview.

## Task2: Independent full source auditor

Create trading_system/tree_spec/optionswall_source.py,
tools/check_optionswall_source_parity.py,
tests/tree_spec/test_optionswall_source.py.
Interface audit_optionswall_source(parentroot) -> verificationreport.

- [x] Write normalmissingauditorRED and actualpinnedfixture:
  ```python
  r=api().audit_optionswall_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Candidateclock/age/anchor/sourcefilter/ratio/expiry/firstwall/catches/import/
  signature/constructor drift; sourceblob/HEAD/root/baseline/orderedinventory/
  pathglobals/substitutioncounts/duplicates/missing/syntax allblock.
- [x] `python -B -m pytest tests/tree_spec/test_optionswall_source.py -q --tb=short -p no:cacheprovider` RED.
  Then independentliteralconstants/import/signature inventories, exact2global
  originalAST checks, completeorderedmodulecomparison and literalpin/root/
  baseline/blob gates. Preserve recognizedinputerrors as blockers.
  CLI required--source-root JSON0/2/unrelatedcwd/importguard; readinessfalse.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_optionswall.py tests/tree_spec/test_optionswall_source.py tests/tree_replay/test_pattern_readers.py -q --tb=short -p no:cacheprovider`;
  CLIexplicit retainedparent. Candidate-only ratio/currentprice or staleage
  mutation must be caught by runtimefixtures. Recordterminalresults/hashes.
- [x] Package3files, independenttask/finalreviews, fixfindings, verify and record
  acceptance/usage/AGENTS/master/tracker. No physicaldataread/live/modelclaim.

## Full goal remains

Next actualfulltree/builder, sourceoperationclocklevelmap, revalidationbinding,
causalproviders/caller/lifecycle/otherproducers/simulator/dataset/models/evaluation.
Syntheticartifacttests do not answer historicalfeedcoverage orhumanGCquestion.

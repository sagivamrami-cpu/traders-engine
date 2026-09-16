# Original stretch calculation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Execute complete original stretch calculation as a revalidation dependency.
**Architecture:** Source projection over explicit offline fetch/shape ports,
real range/EMA functions; independent inert audit and source-characterization tests.
**Tech Stack:** Python, pandas, dataclasses, AST, pytest.
**Spec:** docs/architecture/STRETCH-SOURCE-CONTRACT.md

## Global constraints

- Existing approved feature checkout, preserve unrelated work; apply_patch only.
- Exact sourcecommit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and spec blob pins.
- No retainedsource execution, network/acquisition, datasets/training/live/commits/cleanup.
- Main inline critical-path implementation; independent review sidecars, no nestedagents.
- Preserve actual14period +/-halfADR, not misleading source prose.
- This does not depend on pending final claim-verifier review; do not certify it.

## Task1: Complete calculation and rendering

Create trading_system/tree_replay/_vendor/stretch.py,
tests/tree_replay/test_stretch.py, docs/architecture/STRETCH-SOURCE-USAGE.md.
Consumes real tr.emas/ranges.tr_levels/weekly_from_daily; source fetch/shape ports.
Produces StretchReader(source).state(symbol), ._dev_from_cloud(symbol,tf,days),
original Stretch methods/properties and _atr(df,n=14).

- [x] Write normal missingmodule RED tests using importlib.util.find_spec assertion.
  ```python
  assert importlib.util.find_spec('trading_system.tree_replay._vendor.stretch') is not None
  # ports daily fixture: old ranges differ; last14 prior ranges20, current O100
  s = api().StretchReader(ports).state('OANDA:XAUUSD')
  assert (s.adr,s.rail_hi,s.rail_lo,s.budget_used,s.beyond)==(20.,110.,90.,1.3,.3)
  assert s.direction=='לונג' and s.contradicts('לונג') and not s.contradicts('שורט')
  ```
  Mirror shorts; budget1.25/beyond0 boundaries; current excluded; missingdaily,
  daily14row warmup/zero range/shape false/exception; real20day splice threshold.
  Deviations actual60row linearframe =>12.25,59rows orzeroATR=>omitted, onefailed
  timeframe doesnot cancel others. Record all actual request identities/order.
  Nonextended still reads3frames; no extrapolation from windowrequest to trim.
  Render exact side/tier/units and biggestabs cloud deviation; inputframes unchanged.
- [x] Run `python -B -m pytest tests/tree_replay/test_stretch.py -q --tb=short -p no:cacheprovider`; confirm normal assertionRED.
- [x] Extract selected sourceAST without execution; preserve spec constants/class/_atr;
  create class and six exact call replacements as specified.
  ```python
  class StretchReader:
      def __init__(self, source):
          self.source = source
  ```
  Import actual tr and ranges; copy literal BUDGET_MIN from pinnedrails, no liveimport.
- [x] Run focusedGREEN and range/correction/EMA integration; usage shows ports,
  original discrepancies, rawprovider limits and full remaining master scope.
  Package full3files and request independent spec/qualityreview when available.

## Task2: Source and dependency audit

Create trading_system/tree_spec/stretch_source.py,
tools/check_stretch_source_parity.py, tests/tree_spec/test_stretch_source.py.
Consumes fullTask1module, originalsource and existing range/strictEMA auditors.
Produces audit_stretch_source(parentroot) report; explicit CLI --source-root.

- [x] NormalRED tests: missingauditor assertion, expected VERIFIED/no blockers and
  false readiness; mutate budget/beyond/deviation/render/ATR/request order/depth/
  shape horizon/range call/constructor/import/signatures. Mutate source blobs,
  pins/root/baseline/missingfile and actual range/EMA dependency; guard no imports.
  ```python
  r=api().audit_stretch_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers']==[]
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
- [x] Implement ordered AST projection with exact counts using existing inert
  helpers; source files pinned independently. Invoke check_range_source_parity
  and check_levelmap_source_parity._audit_strict_ema for dependencies only.
  Source parentroot/chart-desk passed explicitly; failures propagate with
  DEPENDENCY prefix; no candidate/source module execution. CLI requiredarg0/2.
- [x] Run focusedaudit and combined tests, explicitCLI from unrelatedcwd and
  importguard. Package3files; independent task and combined final reviews.
- [x] Record current verification and acceptance only after reviews complete;
  update master/tracker/memory. If reviewer unavailable preserve pending gate.

## Continuation

Original full EMA/deep/calendars/tree revalidation and distinct causal lifecycle
feeds remain before full resolver. Do not stop at a supplied boolean or a source
port and call it historical replay. Full master B-I obligations remain binding.

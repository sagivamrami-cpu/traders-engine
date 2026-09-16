# TR vector memory and daily pivot implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Supply actual original vector memory/pivots to fulltree readers.
**Architecture:** Pure defaultnonauction specialization plus exact daily pivots;
independent fullordered audit, real inheritedPVSRA. No causalprovider claims.
**Tech Stack:** Python/pandas/AST/pytest.
**Spec:** docs/architecture/TREE-TR-MEMORY-SOURCE-CONTRACT.md

## Global constraints

- Approved existing feature checkout; main inline criticalpath, independent
  review sidecars; no nestedagents, commits, cleanup or unrelatedchanges.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
  chartdesk/tr.py8297c712d20404880d4d8949e96efbf48613909c.
- Source read/ASTparse only, no originalexecution/live/data/labels/models.
- Preserve original raw semantics; defaultnonauction only. No invented signals,
  timestamps, normalization, instrumentalias or readiness.
- Main has read originalvector_zones/daily_pivots and all fulltree consumers.

## Task1: Pure original memory and pivot runtime

Create trading_system/tree_replay/_vendor/tree_tr.py,
tests/tree_replay/test_tree_tr.py, docs/architecture/TREE-TR-MEMORY-USAGE.md.
Consumes pandasframe and optional actualPVSRAframe. Produces
vector_zones(df,pv=None,*,zone_from='body',cleared_by='wick',max_zones=500)
and daily_pivots(daily,include_m=True), sourceDataFrame/dict outputs.

- [x] Write normalmissingmoduleRED with lazy api() assertion before import.
  Literal zones: body10..12; continuous overlap=>open0; departure14..15 then
  boundarytouch12=>closed1; repeatedoverlap=>touches2. Compare wick/body
  geometry and clearing policies; lastclimaxopen0; onlyclimax notrising;
  availablefirstFalse/lastTrue still empty; missingavailableempty; max_zones
  and index-time versus positional semantics. No generatedexpectedoracles.
  ```python
  assert api().daily_pivots(daily)['PP'] == 10.
  # penultimate high12 low8 close10 gives R1=12,R2=14,R3=16,S1=8,S2=6,S3=4
  # M0..5 =5,7,9,11,13,15; later currentrow999 cannot change these.
  ```
  Real PVSRA:10ordinaryrows then a3xvolume climax; verify actualzone geometry
  and returntracking, zero/missingvolume absence. Empty/one-row pivots, noM.
- [x] `python -B -m pytest tests/tree_replay/test_tree_tr.py -q --tb=short -p no:cacheprovider` must fail normalmissingmodule.
- [x] Inert AST select exact vector_zones,daily_pivots; signaturecheck against
  fulloriginalsignature in spec, remove last2kwonly/defaults; exactoncecall
  replacement via tracker_admission_source._replace_exact. Apply_patch only.
  ```python
  node.args.kwonlyargs = node.args.kwonlyargs[:-2]
  node.args.kw_defaults = node.args.kw_defaults[:-2]
  _replace_exact(node, 'pvsra(df, auction=auction, session_tz=session_tz)', 'pvsra(df)')
  ```
- [x] GREEN:
  `python -B -m pytest tests/tree_replay/test_tree_tr.py tests/tree_replay/test_reversal.py tests/tree_replay/test_reversal_source.py -q --tb=short -p no:cacheprovider`.
- [ ] Document interface/rawlimits, package3files, independenttask spec/qualityreview.



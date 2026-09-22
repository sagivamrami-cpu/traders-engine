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

## Task2: Whole projection and dependency audit

Create trading_system/tree_spec/tree_tr_source.py,
tools/check_tree_tr_source_parity.py, tests/tree_spec/test_tree_tr_source.py.
Consumes explicitparentroot; produces audit_tree_tr_source(parentroot) report.

- [ ] Write missingauditorRED and literalverified/no-readiness case:
  ```python
  r=api().audit_tree_tr_source(SOURCE)
  assert r['source_subset_verified'] and not r['blockers']
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Mutate departurecondition, aftermask, overlapboundaries/count, geometry,
  max_zones, availableindex, pivotrow/formulas/include_m/imports/signature;
  mutate actualPVSRAdependency. Sourceblob/root/HEAD/baseline/missing/syntax
  and projectionduplicates/order/substitution/signature drift mustblock.
- [ ] Run RED then implement independentprojection and literalidentity,
  fullorderedmodule comparison and actual
  tools.check_reversal_source_parity.check_source_parity(parent/'chart-desk').
  Retain dependencyfailure/errorsinclfalseempty. RequiredCLI --source-root,
  JSON0/2, unrelatedcwd and freshprocess forbiddenchartdesk/floor/tree_replay
  importguard. Alwaysfalse readiness.
- [ ] GREEN:
  `python -B -m pytest tests/tree_replay/test_tree_tr.py tests/tree_spec/test_tree_tr_source.py tests/tree_replay/test_reversal.py tests/tree_replay/test_reversal_source.py -q --tb=short -p no:cacheprovider`;
  `python -B tools/check_tree_tr_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
  Candidateonly behavioralmutation of departure rule must fail test.
- [ ] Package3files; independenttask and finalcomponentreview; record exact
  results/hashes and acceptedstatus, update plan/AGENTS/master/tracker.

## Full-goal continuation

Next actualWM/liquidity/Brinks/checklist/options readers, fulltree+builder and
operationclockmap binding, then causalproviders/caller/lifecycle and remaining
producers/simulator/dataset/model/evaluation. Human dependencies do not stop
unrelated synthetic engineering. This component is not wholeplan completion.


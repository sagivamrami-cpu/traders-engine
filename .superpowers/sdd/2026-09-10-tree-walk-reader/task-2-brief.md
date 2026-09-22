# Task2 requirements

## Global constraints

- Existing approved feature checkout; main inline critical path and independent
  review sidecars. No nestedagents/commits/cleanup/unrelated changes.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, tree.py
  fdb439a39bbd35230e421c0319c6be0e2fbfbc1d. Original source read/parse only.
- No rewritten rules, provider-final Walk/Plan/map/pattern/matrix values,
  default readiness, new thresholds, economic labels, data or live actions.
- House/strict, original missing/negative/error distinctions, separate clocks,
  full source bodies and actual dependencies required. Fixed-T APIs unchanged.

## Task2: Whole tree projection and dependency proof

Create trading_system/tree_spec/tree_walk_source.py,
tools/check_tree_walk_source_parity.py and tests/tree_spec/test_tree_walk_source.py.
Interface audit_tree_walk_source(parentroot)->report with false readiness.

- [ ] Missing-auditor RED and literalverified fixture:
  ```python
  r = api().audit_tree_walk_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers'] == []
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Runtime AST mutations: missing stage, wrong .15/.33/.35/5 thresholds,
  completed/forming index, trap side, false neutral/fallback, binding to provider
  verdicts, missing actual readers, news15->30/windowtime/reorder, missed strict
  pivot, refusing-plan retention and changed clock laziness. Source mutations
  commit/blob/import/signature/inventory/duplicate/missing/reorder/count/syntax.
  Dependencyfalseempty/trueblocked/error and genuine transitive runtime drift.
- [ ] Run `python -B -m pytest tests/tree_spec/test_tree_walk_source.py -q --tb=short -p no:cacheprovider` for normal RED.
  Implement independent literal authority and full ordered candidate AST proof,
  not a manifest that candidate edits can redefine. Call actual dependency
  auditors for operation-map, pattern, options, memory, stretch, admission,
  revalidation/calendar/watch sessions, EMA/cloud. Correct parentroot versus
  chart-deskroot explicit; preserve every blocker and false readiness.
- [ ] CLI `python -B tools/check_tree_walk_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`
  JSON0/2, invalidroot/missingfiles and unrelatedcwd; subprocess import guard
  prohibits original chartdesk/floor and runtime imports during audit. In-memory
  local-candidate wrongtrap/newswindow/formingrow mutations must fail literal
  behavior fixtures; never execute retained original source.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_tree_walk.py tests/tree_spec/test_tree_walk_source.py tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider`.
  Record terminal results/hashes, task/final independent reviews, source CLI;
  update usage/AGENTS/master/tracker. Leave causalfeeds/caller/otherproducers/
  simulation/data/models explicitly open. Next bind actual TreeReader to
  Revalidation's tree_walk port; no fake finished-tree answer.

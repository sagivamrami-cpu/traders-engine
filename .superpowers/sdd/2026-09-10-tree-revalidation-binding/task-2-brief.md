# Actual tree pending-revalidation binding implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Aged pending revalidation consumes the actual tree and matrix on raw inputs.
**Architecture:** Original two matrix reader functions plus a narrow shared raw-port
facade composing accepted readers outside their source modules, with complete proof.
**Tech Stack:** Python/pandas/pytest/AST.
**Spec:** docs/architecture/TREE-REVALIDATION-BINDING-CONTRACT.md

## Global constraints

- Existing approved feature checkout; no commits/pushes/cleanup/unrelated changes.
  Main inline critical path and independent review sidecars; no nested agents.
- Finish complete tree component's pending final acceptance before binding it.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; matrix.py
  28641487567c457b6922c2a63055659867bb4248. Original source read/parse only.
- No provider-final Walk/matrix/broker verdicts, altered trading rules, cached
  operation times, economic labels, data acquisition or live actions.
- Accepted tree/revalidation/basis/matrix source modules and public fixed-T
  adapters unchanged. New composition stays explicitly not causal-certified.

## Task2: Binding source proof and acceptance

Create `trading_system/tree_spec/tree_revalidation_source.py`,
`tools/check_tree_revalidation_source_parity.py`, and
`tests/tree_spec/test_tree_revalidation_source.py`.

- [ ] Missing-auditor RED and literal full graph verified/not-ready case:
  ```python
  report = api().audit_tree_revalidation_source(SOURCE)
  assert report['source_subset_verified'] and report['blockers'] == []
  assert not report['ready_for_replay'] and not report['ready_for_training']
  ```
  Mutate matrix lookback/dispatch/order/correction-note/return adapter, facade
  provider-final shortcuts/strict override/frozen clocks/eager shadow entry,
  constructor and pending argument forwarding; each must block. Include original
  matrix blob/import/signature/missing/duplicate and genuine tree dependency drift.
  Dependency falseempty/trueblocked/OSError/StopIteration must return blocked.
- [ ] Run `python -B -m pytest tests/tree_spec/test_tree_revalidation_source.py -q --tb=short -p no:cacheprovider` to confirm RED. Implement full ordered projection
  with independent literal authority and exact-count substitutions; actual
  audit_tree_walk_source(parentroot), no supplied child verdict. Reuse audited
  matrix.read_frame; ensure all source-to-pure-reader replacements are explicit.
- [ ] CLI explicit parentroot, JSON0/2, invalid/missing pin and unrelated cwd;
  subprocess import guard for chartdesk/floor/tree_replay. Example:
  `python -B tools/check_tree_revalidation_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_spec/test_tree_revalidation_source.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider`.
  Record terminal evidence, source CLI/hashes, independent task/final reviews.
  Update usage/master/tracker/AGENTS only to accepted scope; full causal providers,
  original market-watch caller/lifecycle/other producers and E-I remain open.



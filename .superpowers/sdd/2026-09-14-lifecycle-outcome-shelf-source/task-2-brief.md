### Task 2: Source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_outcome_shelf_source.py`
- Create: `tools/check_lifecycle_outcome_shelf_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_outcome_shelf_source.py`

- [ ] Start normal RED for missing auditor/runtime and mutations of source
  identity/blob, selected order/signatures/constants, clock/I/O substitutions,
  child identity/projections, malformed child reports and CLI serialization.
- [ ] Implement an inert full AST projection and explicit-root JSON CLI.
  Require actual tracker-admission and lifecycle-gate child audits; pin child
  identities/projections immutably and fail closed on every source/child/CLI
  error.
- [ ] Run focused runtime/source/child suites and retained CLI; obtain Task 2
  review then independent combined final review.
- [ ] On acceptance update usage, tracker, AGENTS and this plan without
  implying resolver-loop, economic-label, replay/dataset/model completion.

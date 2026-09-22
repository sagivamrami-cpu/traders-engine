# SDD ledger — plan: docs/superpowers/plans/2026-09-08-existing-baseline-contracts.md

Baseline branch: plan/tree-to-trained-model-langgraph. Existing user changes preserved.
Initial tests: python -m pytest tests/tree_spec -q — 63 passed.
Preflight table is in the plan; tasks 1 and 2 have disjoint files and no dependency.
Task 1: implemented; independent review findings resolved with RED/GREEN tests.
Task 2: implemented; worker report read, controller rerun 254 passed, independent
review approved bounded supplied-trade arithmetic and snapshot compatibility.
Task 3: accepted. Final tree-spec suite 349 passed in 30.76s; final broad
regression 729 passed in 147.74s with legacy validator files explicitly excluded.
Final source CLI: all six pins verified, replay/training readiness false.
Process adaptations: no commits/cleanup per existing local project plan; source
review uses explicit new files. No trading policy parameters inferred.

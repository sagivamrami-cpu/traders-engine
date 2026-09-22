# SDD ledger — plan: docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md

Workspace ruling: continue on the existing dedicated branch
`plan/tree-to-trained-model-langgraph`; the user-authorized project worktree
already contains the dependent untracked source-projection artifacts. Cost if
wrong: an unrelated dirty artifact could be mistaken for this plan, so each
review must use scoped paths and explicitly inspect status/diff.

## Preflight interface table

| Tasks | Produced / consumed interface | Finding |
| --- | --- | --- |
| 1 -> 2 | Task 1 produces `LifecycleLiveResolver.resolve(state) -> (messages, changed)` and private `(prices, bar_extremes, raw_quotes)` observation; Task 2 parses/audits exactly that module. | Compatible: Task 2 begins only after Task 1 is reviewed. |
| 1 -> 3 | Task 1 provides runtime, usage and direct-suite evidence; Task 3 records acceptance after Task 2/final review. | Compatible: Task 3 does not alter runtime policy. |
| 2 -> 3 | Task 2 produces a fail-closed explicit-root CLI and child-proof report. | Compatible: Task 3 depends on verified CLI, not a readiness promotion. |

Ruling: preserve the accepted narrow two-value evidence interface unchanged and
place the source-exact three-value observation in the new resolver. The source
needs raw `_q` later; widening the prior audited module or re-reading quotes in
the composer would respectively invalidate accepted scope or make a non-source
third observation. Cost if wrong: the new observation duplicates source
acquisition mechanics, so Task 2 must pin it and mutations must fail closed.

Task 1: in progress (base c1b6071)
Task 1: fix round 1/5 (M1-M2 addressed; 119 direct runtime/child tests pass;
scoped re-review clean)
Task 1: complete (uncommitted scoped artifacts; review clean)
Task 2: in progress
Task 2: complete (uncommitted scoped artifacts; review clean)
Task 3: complete (final review PASS; accepted 2026-09-15T004000Z)

# SDD ledger — plan: docs/superpowers/plans/2026-09-15-lifecycle-closed-resolver-source.md

## Setup

- Workspace: current dedicated branch `plan/tree-to-trained-model-langgraph` in
  the shared program checkout. `git-dir` equals `git-common-dir`, so it is not
  a linked worktree. Ruling: retain this existing, user-scoped branch rather
  than create a second worktree over a large intentional dirty program;
  concurrent implementations remain serial. Cost if wrong: an unrelated
  local edit could obscure a review diff, mitigated by scoped paths and
  pre/post `git status` plus focused verification.
- Base commit for Task 1: `c1b6071633c55376c64f0a98ece843706f420f49`.
- Spec read: `docs/architecture/LIFECYCLE-CLOSED-RESOLVER-SOURCE-INTAKE.md`.

## Preflight interface scan

| Tasks | Producer / consumer | Finding |
| --- | --- | --- |
| 1 → 2 | Task 1 creates `LifecycleClosedResolver.resolve(state, *, now) -> (messages, changed)`; Task 2 parses its vendor text | Compatible; audit must compare an explicit offline adaptation, not execute retained source. |
| 2 → 3 | Task 2 creates verifier, tests and CLI; Task 3 reruns them and records acceptance | Compatible; acceptance has no code-path dependency beyond Task 2 evidence. |
| 1 | Runtime tests require a fake `fetch_corrected(symbol, "15m", 3)` and use exact source geometry | Compatible with spec. `DeskSuccess.observe_bars` is required for closed bars; do not substitute live quote minimum logic. |
| 2 | AST test demands exact three-day fetch, correction gates, strict slice and OPEN ordering | Compatible with Task 1 source-derived composition. |
| 3 | Documentation/status references both prior outputs | Compatible; no readiness promotion allowed. |

Ruling: use a separate closed-bar minimum-success adaptation within the resolver
because source `check()` calls `desk_success.observe_bars(t, since)`, while the
accepted live minimum component additionally depends on fresh quote evidence.
Cost if wrong: an unpinned local adaptation could drift; Task 2 must pin this
exact source branch and require the shared `DeskSuccess`/outcome primitives.

Task 1: fix round 1/5 (I1 addressed, 0 open — exact Hebrew short direction
and discriminatory short minimum/progress regression; no commits because this
intentional program workspace is uncommitted).
Task 1: complete (uncommitted scoped paths, review clean after fix round 1).
Task 2: complete (uncommitted scoped paths, task review clean; 15 audit tests
passed and direct explicit-root CLI VERIFIED).
Task 3: complete (30 combined tests, final review clean, bounded acceptance
recorded). Ruling: retain raw outcome facts as non-economic lifecycle facts;
the next work must build causal replay/economic labelling separately. Cost if
wrong: downstream training could treat status records as P&L labels.

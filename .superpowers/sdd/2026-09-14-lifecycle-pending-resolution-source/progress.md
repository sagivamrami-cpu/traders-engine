# SDD ledger — plan: docs/superpowers/plans/2026-09-14-lifecycle-pending-resolution-source.md

## Pre-flight review

| Tasks/interfaces | Producer → consumer | Finding / ruling |
| --- | --- | --- |
| Task 1 runtime → Task 2 audit | `LifecyclePendingResolution.resolve(trade, *, state, price, bar_extremes) -> (messages, changed)` | Clean: Task 2 audits Task 1's one-trade projection and its explicit ports. |
| Task 1 → deferred OPEN resolver | a successful PENDING result changes only `state` to `OPEN` | Ruling: no same-pass OPEN progression in this plan; a later composed resolver must perform it in source order. Cost if wrong: a future composition could omit source same-pass progression, so its integration contract must test that boundary. |
| accepted outcome/transitions/revalidation → Task 1 | raw cancellation facts, message/terminal mutation, pending validation | Clean: reuse the accepted units; do not duplicate their policy. |
| Task 2 audit → child auditors | existing accepted child projection proofs | Clean: Task 2 must fail closed if a required child proof is not verified. |

Workspace ruling: the current branch is `plan/tree-to-trained-model-langgraph`,
not main/master, but the worktree is intentionally dirty with user-owned
untracked work. No isolation or cleanup action is safe or needed; this plan
touches only its newly named files.

Task 1: in progress. No commit, push, original-source execution, market-data,
state persistence, delivery, economics, dataset or training action is allowed.

Task 1: fix round 1/5 opened after independent review. Root cause: the
directional touch fixtures were nonphysical and non-discriminating, so swapping
low/high could survive; every resolver test also replaced TreeRevalidation.
Ruling: repair test evidence only, retaining the runtime's already-correct
source projection. Cost if wrong: an untested connector could hide a future
constructor/port incompatibility.

Task 1: fix round 1/5 complete (M1 and M2 addressed, re-review clean).
Fresh combined evidence: `72 passed in 6.47s`; re-review
`2026-09-14T083000Z-lifecycle-pending-resolution-task1-rereview.md` PASS.
Task 1: complete (no commits; review clean). Source audit, outer-loop
composition, persistence, economics, dataset and model work remain open.

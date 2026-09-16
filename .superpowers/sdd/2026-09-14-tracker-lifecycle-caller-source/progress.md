# SDD ledger — plan: docs/superpowers/plans/2026-09-14-tracker-lifecycle-caller-source.md

## Pre-flight review

| Tasks/interfaces | Producer → consumer | Finding / ruling |
| --- | --- | --- |
| Task 1 runtime → Task 2 audit | `TrackerLifecycleCaller` module, constructor and three public/semi-public methods | Clean. Task 2 pins the exact interface created by Task 1. |
| Task 1 → accepted lifecycle gate | real `_persist_gated_lifecycle` must precede `source.save` | Clean. This is the explicit selected source tail and test invariant. |
| Task 1 → accepted tracker lock | live wrapper must only turn `LockBusy` into `[]` | Clean. All other exceptions remain observable. |
| retained source identity → audit | current sibling checkout is not at the pinned commit; a separately retained root has the required commit/blob | Ruling: source proofs must use the explicit retained root, never the mutable sibling checkout. Cost if wrong: proof blocks rather than accepting a different source. |

Task 1: in progress. No source module was imported/executed. This plan stays
offline; its scope is caller sequencing only, not the mutation algorithms,
replay or outcomes.

Task 1 review round 1: critical unshared `TrackerLock` instance found. Ruling:
use the source's shared `source.locked(skip_if_busy=True)` policy and add a
real nested-context regression. Reviewer concern about broad `LockBusy` catch
is retained source behavior (public source wrapper catches it around the
`with` body), so it is not changed. Cost if wrong: a later full source body
could surface LockBusy; the future resolver port must preserve its source
exception surface.

Task 1 re-review: shared lock fix passes. Two documentation/coverage fixes
remain: contract must state source owns the policy; callback-raised LockBusy
must be explicitly source-faithful and tested. No new behavior is authorized.

Task 1: complete and accepted. Normal missing-module RED was 12 failures;
fresh combined runtime/consumer proof is 113 passed in 0.87s. Independent
review found and the fix round closed the shared-lock critical issue; scoped
re-review PASS with no findings. Ruling retained: broad LockBusy catch matches
the pinned source wrapper, including a callback-raised LockBusy; it is now
documented and regression-tested. Task 2 is next.

Task 2 review: runtime/auditor/CLI behavior is otherwise sound, but mutation
coverage lacks an independent live-tail corruption and a child-audit identity
miswire. Add only those regressions before acceptance.

Task 2: complete and accepted pending combined final review. Normal missing
auditor RED was 1 failure and missing-module RED 9 failures. Fresh task proof:
11 audit tests passed in33.70s; caller/runtime and prior child suites were
rechecked, and retained-source CLI is VERIFIED with zero blockers/readiness
false. Task review found two mutation gaps; focused revision added live-tail
and child-identity mutation regressions; scoped rereview PASS/no findings.

Task 2 and combined component: accepted041000Z. Final reviewer PASS/no
findings. Final independent proof was70runtime/source/child cases in74.94s;
retained caller CLI VERIFIED with zero blockers and readiness false. Usage,
AGENTS and master tracker updated. Next is source resolver-body/causal artifact
binding; this component remains a caller commit seam only.

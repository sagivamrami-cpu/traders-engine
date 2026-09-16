# SDD ledger — lifecycle gate, parking and retry

Plan: `docs/superpowers/plans/2026-09-13-lifecycle-gate-park-source.md`

Task 1 source runtime is implemented. Normal RED: the first gate test failed
because the module was absent. Current behavioral coverage includes unmatched
pass/persistence, real target verification and receipt demotion, stale versus
contradictory claims, ambiguous receipt paths, first-claim parking/exact
unpark, retry release/stale/expiry and atomic cleanup. Task 2 normal auditor
RED also occurred; the audit/CLI now compare the source projection and actual
three child graphs. Fresh combined proof before review: 160 passed in 20.07s;
retained-source CLI VERIFIED with false replay/training readiness.

No source module was imported/executed and no real queue, network, delivery or
broker effect was used. Task review remains required; full caller/scheduling,
remaining tree branches, economics, data and model work stay open.

Task1 review found an apparent group-destination discrepancy and incomplete
boundary coverage. Direct retained-source evidence resolves it: `_park` stores
`bool(tr.get('to_group'))`, so the source can replay a group-local stale message
as personal when the matched trade lacks that field. Contract/usage now say so;
regression covers it. Added empty/mixed persistence, strict3600 boundary,
replay contradiction/loss and courtesy-enqueue-failure cases. Rereview pending.

Task1, Task2 and final combined review are accepted024000Z. The final reviewer
found a malformed child-report shape boundary; exact bool/list/string validation
and three regressions closed it in final rereview. Fresh final evidence:
162runtime/consumer cases and28source audit/mutation cases, retained CLI
VERIFIED. Component scope remains offline and readiness false. Next intake:
TRACKER-LIFECYCLE-CALLER-SOURCE-INTAKE.md.

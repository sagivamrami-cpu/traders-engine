# Task 2 review — tracker lifecycle caller source audit

Request: `docs/superpowers/plans/2026-09-14-tracker-lifecycle-caller-source.md`,
Task 2.

## Verdict

**Spec compliance: NEEDS_REVISION. Task quality: NEEDS_FIXES.**

The implementation correctly pins source identity, checks both source tails and
the live `LockBusy` wrapper, compares the runtime AST, invokes actual child
audits, and fails closed. Two mutation-test gaps prevent acceptance:

1. The test mutates only the first (closed-bar) changed tail and never proves
   a corrupted `_check_live_locked` tail blocks.
2. Tests do not mutate `CHILD_AUDITS` to prove `tracker_lock` cannot be
   silently mapped to the lifecycle-gate child auditor under a correct key.

Required revision: add focused regressions for each mutation and no other
scope change.

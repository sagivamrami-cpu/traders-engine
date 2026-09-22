# Agent Exchange Review

Reviewer: Codex independent Task 2 reviewer

Target request: `agent-exchange/inbox/codex/2026-09-14T011000Z-lifecycle-gate-park-audit-review.md`

Created at: 2026-09-14T01:10:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: NEEDS_REVISION.
- Task quality: NEEDS_REVISION.

Findings:

1. **M1 — child-audit errors/absence are not reliably fail-closed as blocked JSON with exit 2.** The contract requires any absent, errored, or blocked child audit to block the parent. However, the three child auditors are imported before the audit boundary (`lifecycle_gate_park_source.py:9-11`), so a missing/broken child prevents the parent auditor from loading. At invocation, the child loop catches only `ERRORS` (`:211-221`); `ERRORS` is `INPUT_ERRORS + (StopIteration,)` (`lifecycle_identity_source.py:24`), and the underlying list does not include ordinary `RuntimeError` (`tracker_admission_source.py:130-131`). Such a child failure escapes `audit_lifecycle_gate_park_source`; the CLI directly calls it (`check_lifecycle_gate_park_source_parity.py:21-23`), yielding a traceback/exit 1 rather than the promised JSON blocker/exit 2. The focused test only supplies a child *result* containing blockers (`test_lifecycle_gate_park_source.py:55-61`), not an exception or an absent child.

   Recommendation: make child loading/invocation an explicit fail-closed boundary that converts every ordinary child-load/audit exception into a dependency blocker, and ensure the CLI emits the blocked JSON with exit 2. Add tests for a raised non-`ERRORS` child exception and unavailable child module/audit.

2. **M2 — the requested mutation-resistance proof is materially under-covered.** Task 2 explicitly requires mutations for authority pins, selected order/signatures/decorators, substitutions, constructor sharing, decision order, stale/contradiction distinction, persistence skips, park first-write, raw atomic sequence, and child-audit drift/errors (plan, Task 2). The implementation does construct a full expected AST and enforces substitution counts (`lifecycle_gate_park_source.py:85-174`), which is a sound broad mechanism. But the tests mutate only verifier dispatch (`test_lifecycle_gate_park_source.py:43-52`) and strict expiry (`:64-72`), plus a synthetic child blocker (`:55-61`). The baseline verified test (`:19-24`) does not supply the missing mutation evidence. This leaves the specifically requested adversarial proof of the most sensitive transformations and constructor-sharing/effect-order boundaries absent.

   Recommendation: add targeted vendor/source mutations covering every stated category, including `self.threads = self.outbox.threads`, the stale-versus-contradiction branches, skip-before-blocked-journal ordering, first-write parking, all six atomic-port rewrites/cleanup, and pin/order/signature/decorator drift.

Open questions:

- None. Both gaps are determinable from the scoped static artifacts.

Recommended next action:

Revise the Task 2 auditor/CLI and focused audit tests for M1/M2, then request a fresh independent audit review. Do not advance this source-audit component to combined final review yet.

Verification reviewed:

- PASS — full static read of the requested plan, contract, Task 1 acceptance, auditor, CLI, and focused test module; child-audit interfaces and the projected vendor module were also inspected only as static dependencies.
- PASS — static trace of authority pins, exact AST projection/substitution counts, shared constructor binding, real child-audit calls, readiness fields, explicit-root CLI path, and existing mutation tests.
- NOT RUN — all reported pytest/CLI suites, original retained source, replay runtime, subprocesses, IO, and live effects, as required by the request.

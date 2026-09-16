# Task 1 review: lifecycle live resolver source

Reviewer: Codex

Target request: Direct user request for an independent, read-only Task 1 review.

Created at: 2026-09-15T00:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

- Spec compliance: **PASS**
- Task quality: **FAIL** (M1-M2 evidence gaps)

## Scope reviewed

- `AGENTS.md`, `agent-exchange/README.md`, `agent-exchange/protocol.md`, and the Codex inbox (no actionable new item).
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-brief.md`
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-report.md`
- `docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md`
- `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-INTAKE.md`
- `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-USAGE.md`
- `trading_system/tree_replay/_vendor/lifecycle_live_resolver.py`
- `tests/tree_replay/test_lifecycle_live_resolver.py`
- Direct child interfaces: live evidence, live-resolution evidence, pending resolution, post-fill evidence, minimum success, protection, ordinary resolution, and zone return.
- Pinned retained `chartdesk/tracker.py` lines 2559-2760, read as text only; it was neither imported nor executed.

## Confirmed implementation fidelity

The runtime implements the stated private two-observation boundary: it calls `LifecycleLiveEvidence._live_prices()` first and then calls `source.quote_payload()` exactly once for the raw `_q` equivalent. No composition-time third quote read is present. Its corrected-15m fallback preserves the active PENDING/OPEN-symbol scan, 120-second force age, rejected unverified/`tv_stale` correction, strict newer-than-quote comparison, low/high carry, close replacement, and per-symbol exception continuation from the retained block.

For every priced nonterminal record, it preserves `list(state.items())`, then passes the complete supplied state and the snapshot range map to PENDING. A no-touch PENDING record remains PENDING; a cancellation continues; an OPEN transition falls through in the same pass. The OPEN child order is post-fill, minimum, ambiguity protection, ordinary resolution, then zone return only if the mutable record remains OPEN. Minimum receives `raw_quotes[symbol] or {}` and the bar-extreme membership fact; ordinary receives the actual returned minimum message. Ambiguity appends and continues, correctly suppressing ordinary and zone return.

The usage document is appropriately bounded: it does not claim that the composition is effect-free. It explicitly preserves child-owned outcome-shelf effects and the zone-return revalidation child with its documented offline-port behavior. It makes no replay, dataset, training, model, or live-readiness claim.

## Findings

- **M1 — The required corrected-fallback evidence is materially incomplete.** The sole fallback test uses one stale quote (`age=121`) and confirms only the resulting close as `spot` plus `has_bar_extremes=True`. It does not assert that the carried `(low, high)` values reach PENDING, nor exercise either source rejection (`correction.unverified` and `correction.source == "tv_stale"`), the exact `age == FORCE_BAR_AGE_S` skip boundary, strict newer-than-quote behavior, or a failed symbol continuing to another active symbol. Those are explicit source rules in retained lines 2565-2605 and explicit Task-1 fallback requirements. The direct tests for the older two-part evidence component do not prove this new private copy cannot drift. Add focused regressions for these cases; at least one must prove a fallback wick is forwarded to PENDING as the real low/high pair, not merely as a membership boolean.

- **M2 — Error-to-empty behavior for the second/raw quote observation is not exercised.** The implementation correctly catches `source.quote_payload()` around the raw snapshot, but no test makes that second call fail and proves it becomes `{}` without a third read or a resolver crash. This is a named source/brief requirement. Add a two-read fixture whose first quote payload succeeds through `_live_prices()` and whose second raises; assert exactly two calls, a safe empty quote supplied to minimum success, and normal per-record continuation where a fallback price exists.

The M1-M2 items are evidence/coverage failures rather than a demonstrated current implementation mismatch. They make the claimed exact-fallback proof insufficient, so Task quality cannot yet be accepted.

## TDD evidence assessment

The recorded RED phase is credible and targeted: before the module existed, nine tests failed at the intended missing-module assertion; after creation, the same nine passed. The reported direct-child regression command is appropriate. It is not enough to close M1-M2 because those nine tests leave the listed source mutations green.

## Recommended next action

Keep the runtime and its bounded scope. Add the M1-M2 tests first, demonstrate that the relevant fallback/error mutations fail, rerun the focused resolver and direct-child suites, then request a Task-1 re-review. Static source audit, caller binding, persistence/delivery, economic labels, replay, dataset, training, model promotion, and live trading remain out of scope.

## Verification reviewed

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_lifecycle_open_protection.py tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

PASS: `111 passed in 1.10s`.

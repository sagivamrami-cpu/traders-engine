# Task 2: Static source proof and fail-closed CLI

Implement only Task 2 from
`docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md`, using
`docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-INTAKE.md` as binding
authority. Task 1 is accepted; do not change it except through a separately
requested fix round.

## Files

- Create `trading_system/tree_spec/lifecycle_live_resolver_source.py`.
- Create `tools/check_lifecycle_live_resolver_source_parity.py`.
- Create `tests/tree_spec/test_lifecycle_live_resolver_source.py`.
- Append a full report to
  `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-2-report.md`.

## Pinned source and safety

Read/parse only (never import/execute) retained
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk/chartdesk/tracker.py`, source
commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`. Check that explicit root is
exactly the retained `chart-desk` repository root and that baseline commit,
HEAD and blob all match. Do not alter accepted child modules, Task 1 runtime,
caller/gate/persistence/delivery or source code.

## Required auditor contract

Create `audit_lifecycle_live_resolver_source(source_root) -> dict` with only
schema-valid reports. On every error, malformed child, root/source identity
mismatch, parser failure, runtime mismatch or serialization failure, return
`status=BLOCKED`, `source_subset_verified=false`, non-empty string blockers,
and `ready_for_replay=false`, `ready_for_training=false`.

For valid source, require pinned physical behavior from `_check_live_locked`
lines 2559–2760 and compare the Task-1 runtime AST to the explicitly permitted
projection. The physical/audited contract must include:

1. `prices = _live_prices()` before the raw `_q` read; the raw-read error
   fallback to `{}`; then one clock read and active PENDING/OPEN symbol set.
2. Exact corrected `15m, 2` fallback rules: force-age `<=`, unverified/
   `tv_stale` reject, UTC final bar timestamp, strict `> now - age` winner,
   carried `(low, high)` and close, per-symbol `except: continue`.
3. no-price early return, then `list(d.items())`, terminal and missing-price
   skips.
4. PENDING branch before OPEN; the source PENDING success can become OPEN in
   the same loop. Cancellation continues; never call OPEN for it.
5. OPEN child order: post-fill, minimum with raw `_q.get(symbol) or {}` and
   bar-extreme membership, ambiguity protection then source `continue`,
   ordinary with actual minimum, and zone return only while state remains OPEN.
6. Aggregate message order/change flags, no direct load/save/gate/delivery
   operation by the Task-1 runtime body. Do not claim inherited children are
   effect-free.

Require accepted child reports by exact configured identity and expected source
projection names for: lifecycle live evidence, pending resolution, OPEN
post-fill evidence, OPEN minimum success, OPEN protection, OPEN ordinary
resolution, and OPEN zone return. Use their existing audit functions; verify
the child report JSON shape, `VERIFIED`, no blockers, pinned commit and both
readiness flags false. Record children in parent dependencies.

Create an explicit-root CLI. It must require `--source-root`, print only valid
JSON, exit `0` only on valid `VERIFIED`, otherwise exit `2`, and keep both
readiness flags false even on argument/audit/report/serialization failures.

## TDD requirements

Tests must start RED because the auditor/CLI are missing. Add source/runtime
mutations that prove detection of each category: quote-order/raw-error fallback,
force-age or strict-freshness drift, range tuple/close drift, scan/order/skip
drift, PENDING no-fall-through or cancellation non-continue, child order,
ambiguity continuation, ordinary-terminal zone suppression, raw-quote
forwarding, source root/commit/blob mismatch, child identity/malformed report,
and CLI missing-root/malformed/serialization behavior. At least one mutation
must show that adding a third quote read or losing the raw quote forwarded to
minimum fails audit. Do not use retained source execution in tests.

Run the audit suite, Task 1/runtime direct-child suite and explicit-root CLI.
Put exact RED/GREEN/mutation/CLI evidence and changed paths in the report.
Do not commit/push, spawn subagents or claim full caller/replay/dataset/
training/model/live readiness.

# Task 1: Source-ordered runtime kernel

Implement only Task 1 from
`docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md` using
`docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-INTAKE.md` as authority.

## Files

- Create `trading_system/tree_replay/_vendor/lifecycle_live_resolver.py`.
- Create `tests/tree_replay/test_lifecycle_live_resolver.py`.
- Create `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-USAGE.md`.
- Append a full report to
  `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-report.md`.

## Required interface

`LifecycleLiveResolver(source).resolve(state: dict) -> tuple[list[tuple[str,
bool]], bool]`. The supplied state is mutable. It must return source-ordered
messages and one aggregate changed flag. No loading, saving, locking, gating,
delivery, broker action, replay/dataset/training/model behavior is permitted.

## Required behavior

Read retained source only, never import or execute it. Pin source behavior from
`chart-desk/chartdesk/tracker.py::_check_live_locked`, lines 2559–2760, at
commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

The resolver owns a private snapshot that makes exactly two quote observations:
first accepted `LifecycleLiveEvidence(source)._live_prices()`, then one
`source.quote_payload()` under source error-to-empty behavior. It returns
`prices`, `bar_extremes` and `raw_quotes`. Preserve the source corrected 15m
fallback over active PENDING/OPEN symbols exactly, including `FORCE_BAR_AGE_S`,
unverified/tv_stale skip, strictly fresher bar selection, low/high carry and
per-symbol error continuation. Do not call `quote_payload()` a third time.

If no prices, return `([], False)`. Iterate `list(state.items())`; skip
STOPPED/DONE/CANCELLED and no-price records. For PENDING, call accepted
`LifecyclePendingResolution`. Its success must fall through in the same pass
when it set state OPEN; cancellation remains terminal and moves to the next
record. For OPEN compose, in this exact order: accepted post-fill evidence,
accepted minimum success (with matching `raw_quotes[symbol] or {}` and
bar-extreme membership), accepted ambiguity protection (changed means append
and continue), accepted ordinary resolution (with the actual returned minimum
message), then accepted zone return only if the same record is still OPEN.

Reuse child components; do not copy their policies. The existing
`LifecycleLiveResolutionEvidence.collect` must stay unchanged. Retain all
accepted descendants' documented offline-port effects. In particular, do not
claim the composed resolver is effect-free merely because its own direct body
does not save/deliver.

## TDD and evidence

Write the tests first and run them before production code. The RED report must
show the intended missing-module/import failure. Tests must prove two quote
reads, raw quote forwarding, no-price/terminal/missing-price skips, fallback
range behavior, pending no-touch/cancel/same-pass fill behavior, child ordering,
minimum-before-ambiguity, ambiguity continuation, ordinary terminal suppressing
zone return and unchanged OPEN reaching zone return. Use real classes with an
explicit offline source fixture; only replace children where necessary to
observe order. Include the exact commands/results in the report.

Run the focused suite and relevant direct child suites before reporting. Do not
commit, push, spawn subagents, edit source-audit/CLI files, alter accepted child
modules, modify unrelated artifacts, or claim full resolver/replay/training/
model/live readiness.

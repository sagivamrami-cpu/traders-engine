# Task 1 brief — lifecycle live-resolution evidence collector

Plan: `docs/superpowers/plans/2026-09-14-lifecycle-live-resolution-evidence-source.md`

## Files

- Create `trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py`
- Create `tests/tree_replay/test_lifecycle_live_resolution_evidence.py`
- Create `docs/architecture/LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-USAGE.md`

## Exact scope

Recover only the leading evidence block from retained source `_check_live_locked`
after its supplied state is loaded and before the later `if not prices: return []`
guard. Create `LifecycleLiveResolutionEvidence(source)`. Its collector accepts a
supplied state mapping and returns `(prices, bar_extremes)`, where `prices` is a
symbol-to-float map and `bar_extremes` maps a symbol to `(low, high)` floats.
Use the accepted `LifecycleLiveEvidence(source)._live_prices()` as the initial
fresh-price map; do not duplicate that implementation.

After obtaining this map, mirror source behavior exactly over supplied ports:
read `source.quote_payload()` with top-level broad failure -> `{}`, get
`source.now_epoch()`, iterate the set of `PENDING`/`OPEN` symbols, calculate raw
quote age, skip fallback iff the symbol is fresh and `age <= FORCE_BAR_AGE_S`,
and otherwise call `source.fetch_corrected(symbol, "15m", 2)`. A correction with
`unverified=True` or `source == "tv_stale"` is skipped. Per-symbol fallback
errors are skipped. A fallback wins only when no initial price exists or its
final UTC timestamp is strictly greater than `now - age`; preserve final low and
high as `(low, high)` and use final close as price.

The only source adaptations are: `_load()` becomes the collector argument,
`basis.fetch_corrected` becomes the supplied port, `QUOTES.read_text` becomes
the supplied raw quote port, and `time.time()` becomes supplied operation clock.
Do not implement source `if not prices: return []` because the collector returns
its evidence to a future resolver body rather than running resolution.

## Tests

Write the normal missing-module RED tests first and observe their expected
failure. Cover active state filtering, exact `FORCE_BAR_AGE_S` boundary,
request identity, correction rejection, timestamp strictness, range carry,
fallback sibling isolation, top-level raw payload failure, and no mutation of
the supplied state/frame/correction. Include a negative proof that no
transition/outcome/caller ports are invoked or needed. Use only in-memory pandas
frames and test sources.

## Constraints

Read `docs/architecture/LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-INTAKE.md`
and the full plan first. Never execute retained source. No state mutation,
resolver decision, fill/revalidation, target/stop/progress logic, outcome,
gate/save/delivery, feed/broker I/O, replay, economic/dataset/model/training or
readiness behavior. Do not dispatch subagents, commit, push, or alter unrelated
files.

Write a complete report to
`.superpowers/sdd/2026-09-14-lifecycle-live-resolution-evidence-source/task-1-report.md`
and reply only status, changed paths, test results and concerns.

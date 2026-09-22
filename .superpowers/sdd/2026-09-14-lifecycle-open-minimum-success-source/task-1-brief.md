# Task 1: Runtime and focused tests

Implement only Task 1 from
`docs/superpowers/plans/2026-09-14-lifecycle-open-minimum-success-source.md`.
Read its source intake first.

Create the runtime, focused tests and usage document named in the plan.
Expose:

```python
LifecycleOpenMinimumSuccess(source).resolve(
    trade, *, low, high, spot, quote, has_bar_extremes, minimum_message
) -> tuple[list[tuple[str, bool]], bool, str | None]
```

Preserve retained source lines 2690–2704 at the pinned tracker source.
`quote` is the caller-supplied raw record for this symbol, and
`has_bar_extremes` represents membership in the caller's forming-bar map.
Do not acquire quote/bars, resolve ambiguity/targets/protection, persist,
deliver or create economic/replay/dataset/training/model behavior.

TDD must prove:

- an existing bar minimum records one message/fact and only advances a progress
  step when protection is untouched;
- an exact fresh quote minimum is observed only with matching `lp`, legal age,
  fill-time ordering and no forming-bar extremes;
- stale quote, wrong `lp`, protective touch and bar-extreme membership cannot
  create a quote minimum;
- long uses high and short uses low for the progress-step calculation;
- no minimum leaves all input trade/source outcome ports unchanged;
- every success creates exactly raw `minimum_success`, not an economic label.

Use accepted helpers, source clock only, and test source ports that fail if
data acquisition/persistence/delivery occurs. Do not execute or import the
retained source. Write report to
`.superpowers/sdd/2026-09-14-lifecycle-open-minimum-success-source/task-1-report.md`
with RED/GREEN commands/results, files changed, scope concerns and status.
Do not commit, push, change unrelated files or spawn subagents.

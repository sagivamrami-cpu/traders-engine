# Task 1: Runtime source projection

Implement Task 1 only from `docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md` and read `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-INTAKE.md` first.

Create runtime, focused tests and usage documentation. Expose:

```python
LifecycleOpenZoneReturn(source).resolve(trade, *, spot: float) -> tuple[list[tuple[str, bool]], bool]
```

Use accepted entry-band, lifecycle transitions/voice, DeskSuccess and private
Revalidation helpers. Preserve retained source helper behavior at lines
1046–1106:

- no excursion (`0/0`) is a no-op;
- a previous marker suppresses a repeated return until count of hit targets is
  greater than marker target count; malformed marker counts as zero;
- short uses `spot >= zone_low`, long uses `spot <= zone_high`;
- compose source journey and three-way label-only entry recheck;
- caught revalidation becomes valid but unverified;
- emit exactly one `(message, to_group)` and mutate only `zone_return_at`.

TDD must prove long/short, outside band, no excursion, repeated suppression,
target-only rearm, malformed marker, valid/invalid/unverified/caught-error
recheck text, and that it never acquires market data, persists, delivers,
changes terminal/protective/target fields or writes an outcome. The retention
source must be read only, never imported/executed. Write full report to
`.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-1-report.md`
with RED/GREEN evidence. Do not commit/push/spawn or touch unrelated files.

# Task 1 precision fix review

Prior diff: task-1-review.diff.md. Prior gate approved. Parent then reproduced
pandas Timestamp at last close +300s +1ns being accepted with budget300s.
Updated plan explicitly restricts input timestamps to microsecond-exact values.

Only runtime change is _utc and its module docstring. New body:

```python
def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    if getattr(value, "nanosecond", 0) != 0:
        raise ValueError(f"{field} must be microsecond-exact")
    utc = value.astimezone(timezone.utc)
    native = datetime(
        utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second,
        utc.microsecond, tzinfo=timezone.utc,
    )
    if utc != native:
        raise ValueError(f"{field} must be microsecond-exact")
    return native
```

Old body returned value.astimezone(timezone.utc) immediately after awareness
validation. No selector/economic/EMA arithmetic changed.

Tests: last103lines of tests/tree_replay/test_bars.py contain new timestamp
regressions; read that exact section as fix coverage. Worker detailed report
appendix in agent-exchange/status/2026-09-09T000000Z-worker-asof-bars.md records
RED23failed138passed, GREEN161passed. Parent combined rerun in progress.

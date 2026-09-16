# Explicit shared operation clock

`ReplayClock` holds caller-supplied aware microsecond UTC time; no wall-clock read
or sleeping occurs. It permits equal/forward time only, validating before mutation.
It does not certify any input availability or implement a publication scheduler.

```python
from trading_system.tree_replay.clock import ReplayClock
from trading_system.tree_replay.tracker_storage import CausalTrackerStorage

clock = ReplayClock(decision_time)
storage = CausalTrackerStorage(seed=tracker_seed, decision_time=decision_time, clock=clock)
clock.advance_to(next_operation_time)
rows = storage.load()  # Checks the same artifact against the NEW operation time.
```

The seed and times above are supplied caller inputs, not market defaults.
`CausalQuoteReader` and `CausalWatchLog` accept the same optional `clock` parameter.
At binding its type must be exactly ReplayClock, and now must equal decision_time.
Omitting the parameter preserves existing fixed-time behavior. No existing source
projection, threshold or data fallback is changed.

Advancing the clock does not reset state, creations, quarantines or log chunks.
Quote freshness, session calculation, trace times and artifact snapshots use the
current clock. Already-open log readers keep their captured byte prefix. Crossing
coverage or reaching unknown evidence still causes guarded reads/writes to fail;
source catches do not remove provider failure traces. Time may advance even when
an artifact is missing. Clock.now is read-only; use advance_to, not private fields.

`log.advance_to(T)` retains its original artifact guard. With a bound clock it
advances the shared clock only after that guard; other contexts then observe T.
An application with scheduled publications should own the clock privately and
advance it through its coordinator, not bypass that schedule using a child log.
No implicit thread safety, rollback, elapsed-time inference or checkpoint exists.

This is a prerequisite for combined admission context. It is not the whole watch
loop or a guarantee of historical feed coverage, OS timing, trade fills or training.
Run `python -m pytest tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_frames.py -q --tb=short`.

# Causal admission memory evidence

`trading_system.tree_replay.state` is an offline evidence store, not a simulator.
It preserves what a source-advisory tracker, episode map and rejection log said
as of a decision. It does not generate their transitions or certify provenance.

```python
from datetime import datetime, timezone
from trading_system.tree_replay.state import (
    MemoryEvent, MemoryJournal, memory_asof, checkpoint_memory, restore_memory,
)

t = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
event = MemoryEvent(
    event_id='observation-1', sequence=1, stream='tracker', key='trade-1',
    observed_at=t, available_at=t,
    payload_json='{"symbol":"OANDA:XAUUSD","state":"PENDING"}',
)
journal = MemoryJournal(
    journal_id='synthetic-example', origin='supplied_source_advisory',
    start_at=t, covered_through=t, complete=True, events=(event,),
)
snapshot = memory_asof(journal, t)
assert snapshot['tracker_state']['trade-1']['state'] == 'PENDING'
assert snapshot['replay_ready'] is False
restored = restore_memory(checkpoint_memory(journal))
assert restored == journal
```

## Contracts

- `complete=True` explicitly attests complete state history over
  `[start_at, covered_through]`. No records plus incomplete history is not empty
  state. Queries outside coverage return UNAVAILABLE with null state outputs.
- Event sequence is globally unique/increasing and publication time is
  nondecreasing. Equal-time sequence order is preserved. Wrong ordering is
  rejected, never silently sorted. Event IDs are globally unique.
- Tracker/episode events replace the entire row at `key`. Rejections append,
  with `key == event_id`. No deletion command or implicit row merge exists.
- Both timestamps must be aware, microsecond-exact and observed <= available.
  Numeric source `ts` and tracker `resolved_ts` cannot exceed event observation.
  Epoch comparison uses original JSON decimal tokens, avoiding binary-float
  artifacts and rejecting finer future fractions before JSON float rounding.
- Payload is immutable canonical JSON text. Duplicate keys, nonfinite numbers,
  non-object roots and non-UTF8 text are rejected. Missing source fields remain
  visible for downstream source gates to handle; malformed rows are not dropped.
- Actual T selects published events only. `event_trace` carries their times,
  sequence, keys and payload hashes. Later publications do not alter an earlier
  snapshot or its hash. Output objects are detached from journal memory.
- Checkpoints contain full history with schema/checksum. Restore checks fields,
  canonical timestamps/payload, ordering and coverage even with a recomputed
  checksum. This checksum detects corruption, not malicious forgery or false
  provenance. It is not cryptographic authentication of market history.

The only supported origin is supplied_source_advisory. Do not insert TP1 economic
exits as source advisory transitions. This component neither evaluates the actual
OPEN/PENDING exposure gate nor executes post-stop/same-level/episode admission.
Those gates and source-generated lifecycle replay are the next integration work.
No real state/log files, market data, labels, model or live service is accessed.

Verification: `python -m pytest tests/tree_replay/test_state.py -q --tb=short`.

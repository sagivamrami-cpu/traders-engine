# Causal watch-state storage

This artifact adapter preserves the original market-watch persistence statements,
separately from tracker state. It performs no live file IO and does not run the
full watch loop, its separate lock, or the tracker lifecycle.

```python
from trading_system.tree_replay.watch_storage import CausalWatchStorage

storage = CausalWatchStorage(seed=watch_seed, decision_time=decision_time)
working_state = storage.load()
# Actual original caller updates scalar cooldowns and object episodes here.
storage.save_before_producers(working_state)
# Later original producer processing makes further updates or deletions.
storage.save_final(working_state)
persisted = storage.snapshot()
```

watch_seed must be an exact WatchStateSeed with seed_id/source, observed_at,
available_at, covered_through, status and text. It shares the validated causal
text schema of TrackerStateSeed but is a distinct type. Status is PRESENT with
UTF8-encodable text, or ABSENT/UNREADABLE/UNKNOWN with textNone. Times are aware,
microsecond-exact UTC with observed <= available <= covered. They are caller
evidence, not independent certification of the historical artifact.

Optional `clock=ReplayClock(T)` requires matching initial decision_time and
subsequently uses its current time without resetting state. Availability and
coverage guards run at each operation; advancement does not fill unknown history.
Standalone calls remain at their fixed decision_time.

Source behavior: known absent load yields{}, unreadable or malformed JSON raises.
Other valid JSON roots are not normalized into objects. Mutating a returned value
does not update persisted storage. Explicit saves preserve JSON default spacing,
ASCII escaping, insertion order, scalar/object values and deletions. There is no
tracker shrink/quarantine/creation guard or reread before overwriting. First save
records ensure_directory then write_text; final save only write_text. Serialization
failure preserves the last completed image but can follow the first mkdir attempt.

snapshot gives the last completed saved text with current-time observed/available
and original coverage. Reconstructing another storage from it cannot see unsaved
caller changes. This is one artifact handoff, not full replay checkpoint/resume.
Original filesystem writes are direct/non-atomic. The in-memory implementation
models completed writes only; it does not claim torn-write recovery, permission
fidelity, fsync or atomic transaction guarantees. Historical partial/corrupt text
must be supplied explicitly, not generated as a fabricated filesystem history.

trace returns a detached ordered list of parent/child attempts and errors, including
serialization and data-availability failures. Directory ports represent completed
in-memory attempts, not access to actual directories. Full caller/publication
binding, lifecycle, outcome labels and training remain outside this component.

```powershell
python -m pytest tests/tree_replay/test_watch_storage.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short
```

Independent source audit implementation and component reviews must be accepted
before claiming source parity. Read the latest exchange status, not this example,
to determine acceptance. Synthetic storage tests are not historical market proof.

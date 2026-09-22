# Original tracker lock policy over offline ports

The private `trading_system.tree_replay._vendor.tracker_lock.TrackerLock` retains
original tracker locking policy, not an operating-system lock implementation.
It supplies the context manager consumed by original TrackerAdmission.record
and, later, original resolver callers. No live module is imported or executed.

```python
from trading_system.tree_replay._vendor.tracker_lock import TrackerLock, LockBusy

policy = TrackerLock(supplied_lock_ports)
# The application wires tracker_source.locked to this same policy.locked.
try:
    with policy.locked(wait=30.0, skip_if_busy=True):
        run_supplied_resolver_calls()
except LockBusy:
    pass  # Source caller skips its resolver calls, not necessarily later producers.
```

`supplied_lock_ports` and the resolver callable are application dependencies in
this wiring example, not provided historical backends or a complete replay API.
Every entry point representing one source process must share the policy instance.
Its `held` dictionary models process-global reentrance, not thread-local ownership.
No default successful acquisition, blank busy history or elapsed-time assumption
is supplied. Existing causal state/quote/log/frame providers remain separate.

## Exact port responsibilities

| Method | Required external behavior |
| --- | --- |
| ensure_lock_directory() | Complete or fail the source directory preparation |
| open_lock() | Source append-mode, nontruncating open; return handle with close() |
| try_acquire(handle, timeout=wait) | Return supplied acquisition outcome; expose any actual post-attempt clock/publications through the caller's shared scheduler |
| release(handle) | Release only after source says acquisition succeeded |
| read_busy() | Read original marker text; absent/read failure raises |
| write_busy(text) | Complete or fail writing source's clock string |
| clear_busy() | Delete marker if present; absence is successful, matching missing_ok |
| now_epoch() | Actual operation clock; not always initial decision time |
| warn(text) | Record replay diagnostic, or raise its supplied failure; no real stderr write |

Ports must preserve availability and failed-attempt evidence when bound to real
historical artifacts. Source catches a failed marker read/write/clear; their
failure evidence must survive those catches in that future backend. The policy
alone is not an evidence journal or source-data approval.

## Preserved behavior

Writer default is30seconds; resolver default3seconds; market-watch explicitly
requests30seconds for its resolver wrapper. These are maximum-wait arguments,
not proof that the clock advances by those durations. Real OS polling is separate.
Writers proceed even when acquire returns false. Resolvers raise LockBusy when
continuous refusal age is below120seconds; at120 or above they proceed unlocked.
Malformed marker text is best-effort reset and treated as zero age. Negative and
nonfinite float ages preserve source comparisons, including NaN fail-open.

Nested sections increment/decrement shared depth without reopening/reacquiring,
even inside a writer that proceeded unlocked. A body failure unwinds depth and
releases an acquired handle. Release failure still closes it. Open failure occurs
before the source finally, so there is no invented close on a nonexistent handle.
The component deliberately does not repair questionable source behaviors silently.

Original record computes bias/thesis/born state before entering its lock; state
reload and new record timestamp occur afterwards. Integration tests exercise the
real record method with supplied acquisition-time state and clock changes. They
do not certify all causal providers together or model competing real processes.
Advisory OPEN continues to mean unverified broker fill, not economic execution.

## Verification

```powershell
python -m pytest tests/tree_replay/test_tracker_lock.py tests/tree_spec/test_tracker_lock_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py -q --tb=short
python tools/check_tracker_lock_source_parity.py --source-root C:/path/to/retained-parent
```

The source CLI audits full constants/exception/initializer/methods/imports against
the pinned chart-desk tracker. It parses source only and exits0verified/2blocked.
Both readiness flags remain false. Tests accept TR_TREE_SOURCE_ROOT to locate the
required pinned checkout; missing evidence fails rather than silently skipping.

Required next work: shared scheduler and supplied lock outcomes/publications,
full watch state and caller/resolver lifecycle; other tree branches; economic
simulator/dataset/models/evaluation. No live actions, historical data acquisition,
new outcome labels or training are enabled by this source-policy component.

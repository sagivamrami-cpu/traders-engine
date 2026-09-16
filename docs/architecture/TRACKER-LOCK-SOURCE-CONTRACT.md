# Original tracker lock policy contract

Continuation of approved master C and existing tracker admission source closure.
Preserve pinned chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
chartdesk/tracker.py blobb616b34022e436545d8c1daf85eced51614fd74e.
No trading threshold changes or full historical lock/OS simulation claim.

Private `_vendor/tracker_lock.py` exports original LOCK_TIMEOUT_S,
RESOLVE_LOCK_WAIT_S,LOCK_STALL_S,LockBusy and `TrackerLock(source)`.
One TrackerLock instance represents the source process-global `_HELD` dictionary;
its held field starts with original {"depth":0}. All callers for that process
must share it. This is deliberately not a thread-safe substitute for OS locks.
Methods `_busy_for()` and `locked(*,wait=None,skip_if_busy=False)` preserve full
original bodies, with source references replaced by explicit offline ports only.

Ports: now_epoch()->number; read_busy()->text; write_busy(text); clear_busy();
ensure_lock_directory(); open_lock()->handle supporting close();
try_acquire(handle,timeout=wait)->source acquisition result;
release(handle); warn(text). clear_busy preserves source missing_ok behavior.
Ports own artifact availability, failures, historical time and traced effects.
They are not implemented with fake successful defaults by this component.
No real file, print, sleep, wall clock, network or retained-source execution.

Preserve writer default30/resolver default3, explicit caller override30, nested
depth bypass/unwind, acquire->clear->body->release->close, writer fail-open,
resolver skip until busy age<120 then fail-open (at120 inclusive). The source
float parsing of malformed/negative/nonfinite marker text is retained. A bad
marker best-effort records current time and returns0; failed marker clear/write
is swallowed at the original boundary. No invented clamp or validation changes.
Ensure/open failures stay outside cleanup; acquire/body/release errors obey
original nested finally cleanup. LockBusy remains the exact exported exception.

Audit the complete module AST including imports/constants/class initializer,
original LockBusy, both methods and contextmanager decorator. Exact substitutions
are scoped/count checked; pin commit/baseline/blob independently of runtime.
Return VERIFIED only for this source subset, never ready_for_replay/training.
CLI requires explicit retained parent path, exit0verified/2blocked.

Behavior tests exercise real projected policy with deterministic low-level IO
fixtures: entered/skipped bodies, shared nesting, cleanup on failures, literal
waits and busy boundary, caught failures and dynamic clock. Actual tracker.record
must demonstrably read state/time after acquire while its bias/thesis/quote work
precedes it; controlled ports are not combined causal-provider certification.
Mutation audit tests reject changed timeout/stall/comparison/depth/finally/clock,
extra code, wrong source/baseline and missing files; CLI checked outside cwd.

This prerequisite is not the whole C deliverable. A later shared scheduler must
bind supplied acquisition outcomes, actual elapsed times and publication order
to state/quote/log/frame ports; timeout is not elapsed time. Full watch state,
resolver lifecycle/caller/arbitration and all other master branches remain.

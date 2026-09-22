# Shared-time causal admission providers

`CausalAdmissionContext` connects actual accepted TrackerAdmission and TrackerLock
to real causal frame, tracker-storage, quote and raw-log providers. It is an
in-memory source-consumer context, not the market-watch outer loop or simulator.

```python
from trading_system.tree_replay.admission_context import CausalAdmissionContext

context = CausalAdmissionContext(
    instrument=instrument, decision_time=pass_time,
    tracker_seed=tracker_seed, quote_seed=quote_seed, log_seed=log_seed,
    busy_seed=busy_seed, newline="LF", frame_requests=admission_requests,
    publications=publications, lock_steps=lock_steps,
)
recorded = context.tracker.record(original_selected_plan, variant=source_variant)
evidence = context.report()
```

All variables in this wiring example are explicit caller inputs. Do not rebuild
the Plan from reduced public producer evidence; use the accepted internal handoff.
`recorded` is the original advisory result, NOT a broker fill, a label, a complete
quality approval, or evidence that outer entry gates ran. `report()` always keeps
ready_for_replay and ready_for_training false. It does not automatically certify
its inputs or convert source fallbacks into new trading vetoes.

## Time, publications and artifacts

pass_anchor stays fixed at construction. decision_time advances only through
advance_to(T) or a supplied lock step. The clock is private; no public child log
or storage object is exposed for bypassing publication application. The original
tracker computes bias/thesis/born state before locking and reloads state/timestamps
after acquiring. Existing coherent-T producer interfaces remain unchanged.

Initial inputs are exact TrackerStateSeed, ArtifactSeed(kind quotes/watch_log),
BusyMarkerSeed and tuple[AdmissionFrameRequest,...]. BusyMarkerSeed is a distinct
frozen dataclass sharing TrackerStateSeed's text/time/identity validation, not JSON
state semantics. The busy provider reuses the accepted private causal text backend;
known absence raises on read and unreadable text can be reset by original policy.

Publication fields: publication_id, source, available_at, sequence, channel,
payload. Channels tracker/quotes/watch_log/busy require matching exact seeds whose
available_at equals publication time. Frames use the exact request tuple. Sequence
is a native nonnegative integer. The tuple must already be strictly ordered by
(available_at, sequence) with unique publication IDs, none before pass_anchor.
No implicit sorting, merging or early exposure occurs. A full image explicitly
replaces its channel; generated state/log effects persist until replacement.
Earlier provider traces/effects and captured log-reader prefixes are retained.

Future frames/quotes may be supplied structurally at construction, but only current
published bindings and accepted as-of dependency guards are consumed. Advancing
past a coverage gap does not fill it. Reads then fail until sufficient evidence
is published; clock movement itself is not a data-quality claim. Availability and
coverage remain caller attestations, not proof of historical feed truth, internal
payload correctness or original symbol/contract equivalence.

## Lock steps are evidence, not guessed delays

Every operation has an explicit LockStep: step_id, source, operation, started_at,
completed_at, timeout, acquired, error. Supported operations are prepare/open/
acquire/release/close/warn. For acquire, timeout is a finite native number and a
successful step requires a bool acquired. On supplied error acquired is None.
Other operations require timeout/acquired None. Error is None or UTF-8 text raised
as OSError; other historical exception classes are not simulated by this contract.
All fields are required, IDs unique, and steps are nonoverlapping in supplied order.

An uncontended writer normally consumes prepare, open, acquire, release, close.
A failed acquisition omits release; a stalled resolver may require warn before
close. Actual policy owns the branch. A nested call consumes no new lock steps.
Missing/mismatched operation, time, timeout or handle is OperationUnavailable,
not a default acquired/failed result. A boolean timeout cannot match numeric1.
Matched operations record step identity/source, apply publications through their
supplied completion time, and then return or raise. A30second timeout does not
mean30seconds elapsed. A supplied2second acquisition yields post-lock reads atT+2.

Busy read/write/clear uses causal in-memory text semantics, not scripted filesystem
permissions. UNKNOWN/unpublished/expired evidence blocks these actions; source may
catch the failure, but traces keep it. Known missing clear succeeds. A matched
close attempt ends the local handle even on supplied OSError; this is an explicit
local lifecycle convention, not certification of a historical OS descriptor.
There is no operating-system lock, scheduler thread, process or network activity.

## Ports and evidence

Context exposes load/save, read_symbol/fetch_corrected, quote_payload,
event_log_reader, log, now_epoch, locked and original tracker methods via tracker.
Frame calls instantiate the real AdmissionFrameSource at current time; no fake
matrix scores are used. report() detaches ordered attempt/start/end/error events,
each consumed artifact's traces, storage creation/quarantine effects, frame traces,
and consumed publication/lock-step counts. Unconsumed future payloads are omitted.

AVAILABLE/BLOCKED describe individual attempts, not a new source trading decision.
For example, a known absent quote read can fail while the source deliberately
uses its build-close fallback. Unknown coverage is different evidence. The future
whole-caller/data-quality assessment must preserve that distinction. A successful
record followed by release failure is not rolled back: source storage may already
contain it, even though record raised. No atomic whole-pass transaction is claimed.

All providers/traces are retained in memory. This is not yet a disk-backed ten-year
archive, full checkpoint/resume format, complete watch state, separate market-watch
lock, mixed-clock producer, resolver lifecycle or cross-producer arbitration.
Those and the economic simulator/dataset/model/evaluation remain required.

## Verification

```powershell
python -m pytest tests/tree_replay/test_admission_context.py tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_lock.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_frames.py -q --tb=short
```

Source storage/watch/tracker/lock audits remain unchanged and require the pinned
retained checkout parent. Tests use synthetic evidence and literal expected real
matrix values, not historical market outcomes. No data acquisition or training.

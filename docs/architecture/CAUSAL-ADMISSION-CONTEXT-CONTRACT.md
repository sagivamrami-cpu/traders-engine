# Shared causal admission context contract

Approved master C continuation: compose accepted original TrackerAdmission,
TrackerLock, tracker storage, quote/log and admission frames. No trading rules,
broker execution or historical data certification are added. Existing source
projections/thresholds remain unchanged; coherent-T producer API remains intact.

## Shared clock with compatible standalone contexts

`ReplayClock(decision_time)` holds aware microsecond-exact UTC. `now` is read-only;
`advance_to(T)` accepts equal/forward times, rejects invalid/backward input before
mutation. It does not assert any artifact is available: physical/logical time can
pass while data is missing. No system clock, sleeps or inferred wait durations.

CausalTrackerStorage, CausalQuoteReader and CausalWatchLog accept optional
`clock: ReplayClock | None` alongside the existing required decision_time. Exact
clock type and equality at binding are required. With no clock, every existing
behavior remains unchanged. Bound calls read current clock for availability,
timestamps, sessions, trace and snapshot; shared advance must retain state/effects
and chunk storage. Log.advance_to retains its existing artifact-coverage check;
if bound, it advances the shared clock after that check. A coordinator owns its
clock privately so external log APIs cannot bypass publication application.

## Context and publication model

`CausalAdmissionContext` owns one original TrackerAdmission and one TrackerLock,
one shared clock and separate initial tracker/quotes/watch-log/busy artifacts.
It receives exact instrument, decision_time, explicit newline, admission request
tuple, ordered publication tuple and ordered lock-step tuple. Pass anchor is the
initial time and remains separate from operation time. No default lock success.
All runtime work is in memory; no wall clock, files, subprocesses or network.

Publication has publication_id/source/available_at/sequence/channel/payload.
Order is strictly increasing (available_at,sequence), unique IDs, native nonnegative
sequence; no publication before initial operation time. Channel tracker uses exact
TrackerStateSeed; quotes/watch_log use exact matching ArtifactSeed; busy uses exact
BusyMarkerSeed (same validated text-evidence fields); frames uses the exact tuple
of AdmissionFrameRequest. Text artifact availability must equal publication time.
Frame payload validation is structural; its actual dependency availability remains
the accepted frame provider's responsibility. Nothing is selected early because
it was supplied to the constructor. Equal-time publications apply in sequence.

advance_to(T) validates time before mutations, applies publications through T in
their order and ends at T. Replacing an artifact is an explicit external complete
image, not a merge or fabricated patch. Generated state/log effects persist until
such a replacement. Retain old context traces/effects and already-open log readers.
Coverage gaps are not filled; guards run when a port actually consumes its artifact.
No implicit checkpoint or mid-call OS file-descriptor/concurrency certification.

## Explicit lock-operation evidence

LockStep records step_id/source/operation/started_at/completed_at/timeout/acquired/
error. Operations are prepare/open/acquire/release/close/warn. All fields required;
error is None or a supplied UTF-8 message producing OSError (not a universal OS
exception emulator). An acquire without error requires exact bool acquired and
native finite timeout; other operations require timeout/acquired None. A failed
acquire requires acquired None. Times are ordered; the complete step tuple is
nonoverlapping and IDs unique. No duration is derived from timeout.

Each actual source lock port requires the next matching step, starting exactly
at current operation time; acquire additionally matches timeout. Missing/mismatched
evidence raises and stays traced, never becomes acquired=False or success. A
matched step advances through publications to its supplied completion before
returning/raising its result. Nested source lock sections consume no new steps.
Handle identity/open/close is local and explicit; no operating-system locks.

Busy marker read/write/clear uses a separate causal mutable text artifact. Known
absence raises on read; unreadable raises on read but can be overwritten by the
source's reset. UNKNOWN/unpublished/expired blocks reads and writes, even though
source may catch the error; trace retains it. Clear on known absence succeeds.
This models in-memory artifact semantics, not historical permission failures.

## Actual consumers, evidence and limits

Context implements load/save/read_symbol/fetch_corrected/quote_payload/
event_log_reader/now_epoch/locked/log using accepted components at operation T.
Frame reads construct real accepted AdmissionFrameSource at that T with currently
published requests, no score stubs. Store provider traces on both success/failure.
Original tracker methods run directly; no new gate semantics or reconstructed Plan.
Ordered context trace and detached child traces expose errors even if original
tracker catches them. A source true record result is not full data-quality approval
or a broker fill. report() has readiness false and no economic labels.

Required tests: shared clock compatibility, frozen pass anchor, real causal
matrix->tracker record with all real artifact providers, before/after acquired
clock and state/quote publications, duplicate/OPEN refusal, late inputs and
coverage gaps, source-caught errors retained, raw log selection after same-pass
append, replacement and old-reader isolation, sequential generated state retention,
exact lock-step mismatch/failure/cleanup and reentrance, invalid schedules atomic.
Small fixtures are synthetic, not historical feed or profitability evidence.

Still required: whole market-watch caller and its separate lock/watch-state,
mixed-time producer dependency binding, generated resolver lifecycle/arbitration,
other branches, full replay/checkpoint/coverage, economics/dataset/models/evaluation.

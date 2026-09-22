# Task 4 Independent Review — Closed-Bar Causal Replay Runner

Status: CHANGES_REQUESTED

## Scope and method

Read-only independent review of the Task 4 plan/spec, Task 4 reports and
root-fix reports, complete `causal_replay.py` and `test_causal_replay.py`, the
accepted Task 1 contracts, Task 2 source-order intake, and Task 3
checkpoint/provider-baseline interfaces and acceptance review. The required
startup exchange material and Codex inbox were inspected. No retained source
was imported, compiled, or executed; no implementation/test was changed,
subagent dispatched, or commit created. This file is the sole review artifact.

## Finding

### C1 — Replay events are ledgered by ID but are not causally bound to the provider evidence used by the pass

`ClosedBarCausalReplay._run_anchor()` checks only whether each required event ID
exists and is available (`causal_replay.py:256-260`). `_append()` then records
only the IDs of all time-eligible events (`:234-248`). The runner never reads
`ReplayEvent.payload`, validates it against an admission publication/frame or
reversal input, or applies it to a provider. Lifecycle and producer evaluation
instead consume the independently injected `CausalAdmissionContext` and
`InternalReversalInputs` (`:294-319`).

This violates the Task 4/design requirement to apply supplied earlier/equal
publications causally and to retain ledger event/time bindings. A caller can
replace the payload of an already available `BAR_PUBLICATION` while keeping its
`event_id`, timestamp, and sequence; both runs consume the same event ID and
produce the same ledger digest, even though the immutable evidence bundle is
materially different.

Independent in-memory reproduction (local replay modules only; no retained
source execution):

```text
PROVED_UNBOUND_EVENT_PAYLOAD
3e00f8a00bfe09f0ba204f4975c78f4813f37ac54eca560886311fcfb850a936
```

The probe ran one `NO_CANDIDATE` pass twice. In the second run, event `event-0`
at the same decision time kept its ID/sequence but changed its payload to
`material_bar_identity: replaced-with-different-evidence`. It proved both the
same consumed-event tuple `('event-0',)` and the same final ledger digest.
Task 3's checkpoint bundle fingerprint protects a restore against a substituted
bundle, but it does not correct the one-shot runner: the evidence that drove a
pass remains out-of-band and the raw ledger itself cannot attest to it.

Required correction:

1. Define an exact, fail-closed binding from each lifecycle/producer provider
   artifact/publication/frame/reversal input consumed at a pass to its immutable
   `ReplayEvent` identity and canonical payload reference/digest. Reject or
   emit `BLOCKED` when a required event is unbound, mismatched, unavailable, or
   future; do not accept independently supplied equivalent-looking evidence.
2. Apply only the ordered, eligible bound publication prefix before its anchor;
   maintain the Task 3 provider baseline and exact shared clock while doing so.
3. Carry a deterministic event binding (at least immutable event identity plus
   payload digest/reference and availability/sequence) in each pass record or
   in a record-covered ledger commitment, not IDs alone.
4. Add adversarial tests showing that changing a same-ID, same-time required
   event payload either blocks the pass or changes the bound observation/ledger;
   that a future bound payload cannot influence an earlier lifecycle or producer
   pass; and that a split/resume run with the Task 3 baseline remains exactly
   equal to the corresponding one-shot run after the binding is added.

## Verified boundaries retained

- No normal Task 4 path invokes `TrackerAdmission.record`; selected reports
  become `OBSERVE_ONLY` regardless of activation (`causal_replay.py:339-350`).
  The test monkeypatches `TrackerAdmission.record` to fail if called.
- Unsupported variants are emitted before producer evaluation; missing/invalid
  inputs and producer faults emit `BLOCKED`; `NO_CANDIDATE` remains distinct.
- The nominal source-projected order is present: watch load, pre-producer save,
  supplied-state lifecycle, producer evaluation, final watch save
  (`causal_replay.py:302-328`). Lifecycle uses the accepted closed resolver over
  the supplied admission state/frame port and the in-memory-only tape; there is
  no broker, external delivery, economic, dataset, training, or model call in
  the runner.
- Task 3 baseline/clock restore wiring is used by `run_until()` and `restore()`.
  This finding is specifically that the bundle's event payloads are not bound
  to that already-accepted provider evidence.

## Verification

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider
168 passed in 11.74s
```

The passing focused suite does not cover C1; its future-evidence case appends
an unused future event, rather than changing or binding the provider evidence
used by the earlier pass.

## Verdict

CHANGES_REQUESTED. The safety boundaries and focused suite are sound, but Task
4 cannot be accepted as a causal replay runner until immutable event payloads,
provider evidence, and ledger commitments are tied together.

# Closed-Bar Causal Replay Design

## Status and purpose

Approved design boundary: build an offline, deterministic replay spine that
advances through explicitly available closed-market evidence, runs the accepted
internal-reversal path and tracker lifecycle, and records what the engine knew
and did at each decision.  It is the bridge between the individually verified
tree/lifecycle components and a future historical candidate dataset.

This design deliberately does **not** calculate economic P&L, costs, slippage,
time exit, broker fills, training labels, a fitted model, or any live action.
Those are separate contracts.  A raw lifecycle fact such as `minimum_success`
is not an economic success label.

The user approved this boundary in the project conversation on 2026-09-15.
The user also selected source-faithful tracker activation: a historical pass
creates a tracker record only when its supplied evidence proves that the source
was running with its alert/tracker-recording mode enabled at that time.

## Why this is a separate subsystem

The existing code proves individual causal components but does not yet provide
their outer clock, source-owned pass order, persistent watch/tracker episodes,
cross-producer arbitration, or a resumable run ledger.  Calling those pieces in
an arbitrary order would create a plausible-looking historical result that is
not a replay of the engine.  The replay spine therefore owns scheduling and
audit, while existing components retain all source-specific calculations.

## Scope

### Included in the first vertical replay

- One exact `venue:symbol`, one explicitly selected source variant and one
  supplied, immutable evidence bundle.
- A total ordering over published evidence using `(available_at, sequence)`;
  every item has a unique key.  The run clock may only move forward.
- Closed, available bars only.  A bar whose `closed_at` or `available_at` is
  after the decision time is invisible.  Duplicate/revised bar opens remain
  unsupported and block the affected pass rather than being silently chosen.
- Source-intake and a static audit for the outer market-watch pass order before
  a production replay orchestrator is written.
- Causal watch state and tracker state across passes, using the accepted
  `CausalWatchStorage`, `CausalAdmissionContext`, `CausalTrackerStorage`,
  `TrackerLifecycleCaller`, and `LifecycleClosedResolver` seams.
- Source-faithful tracker activation. A selected plan is always recorded as a
  candidate observation, but it enters tracker state only with explicit,
  time-valid evidence that the original alert-enabled source branch was active.
- Until the source-owned outer-admission gates are implemented and audited, a
  newly selected candidate remains `OBSERVE_ONLY` even when activation evidence
  is present. The first replay advances lifecycle only for records supplied in
  its historical tracker-state evidence; it never fabricates a new tracker row.
- The accepted internal reversal producer (`_evaluate_reversal_asof`) as the
  first executable producer path.  It retains the actual selected `Plan` only
  inside the replay process; public reduced producer evidence is not rebuilt
  into a plan.
- Explicit outcomes for every attempted pass: `PRODUCED`, `NO_CANDIDATE`,
  `BLOCKED`, `SKIPPED`, or `UNSUPPORTED`.  These are replay diagnostics, not
  trade-outcome labels.
- A raw, linked in-memory run ledger: decision snapshots, candidate/plan
  references, tree decisions, tracker mutations, lifecycle messages, source
  traces, and evidence identities.  Every consumed event commits its immutable
  identity, availability/sequence, and canonical payload digest.  An event
  which supplies a provider publication or internal-reversal input additionally
  commits the exact consumer, artifact identity and canonical artifact digest.
  The ledger contains no raw market payload by default.
- Checkpoint/resume in an explicit serializable form, and proof that one
  uninterrupted run equals the same run resumed from any legal checkpoint.

### Explicitly excluded

- Other producer paths, including a synthetic fallback for absent producers.
  They are emitted as `UNSUPPORTED`, with their exact producer identity.
- Inferred feed availability, venue conversion, GC/XAU aliasing, calendar
  synthesis, missing-data defaults, revised-bar selection, or hidden threshold
  choices.
- A counterfactual rule that treats every eligible plan as tracker-recorded.
  That is a distinct future research experiment, not this replay.
- Bypassing or replacing the original outer-admission gates: trading window,
  market-closed condition, producer arbitration, post-stop cooldown, occupied
  slot and same-level duplicate checks. These remain a required later binding.
- A broker/order simulator; fill confirmation; TP1/stop P&L; fees; spread;
  slippage; partials; break-even/trailing; time exits; portfolio exposure.
- Dataset rows, training targets, feature allowlisting, fitting, calibration,
  model selection, profitability claims, shadow trading, or live execution.

## Architecture

```text
immutable evidence bundle
        |
        v
causal schedule --advance--> replay clock
        |                         |
        |                         +--> publication application
        v
source-ordered outer pass adapter
        |\
        | +--> accepted internal reversal producer --> selected plan / diagnostic
        |
        +--> accepted closed tracker lifecycle --> messages / mutated state
        |
        v
raw replay ledger + checkpoint
```

The orchestrator is intentionally thin.  It selects legal evidence at time
`T`, executes the source-ordered pass adapter, and records detached results.
It must not replicate EMA, level-map, reversal, tree, revalidation, lifecycle,
or gate logic already owned by accepted components.

### 1. Evidence and schedule contracts

`ReplayEvidenceBundle` is a frozen, caller-supplied object.  It identifies the
run, exact instrument/variant, requested interval, source pins, initial watch
and tracker artifacts, frame/publication evidence, and ordered pass anchors.
It stores references/IDs and hashes for payloads; it is not a ten-year raw-data
archive.

`ReplayEvent` contains `event_id`, `available_at`, `sequence`, `kind`, exact
source identity, and a typed payload reference.  Ordering is strictly
increasing by `(available_at, sequence)`.  A duplicate, a backward time, an
unknown kind, or a payload whose own availability disagrees with its event
blocks the run before it can affect state.  Sequence resolves equal timestamps;
the engine must never create a tie-breaker from container iteration order.

`ReplayPassAnchor` is an explicit decision time and source-pass identity.  It
may run only after its required evidence has been published.  The initial
version supports the exact internal-reversal/closed-lifecycle source pass.  Any
other pass identity is emitted as `UNSUPPORTED`; it is never approximated.
It also carries exact `TrackerActivationEvidence`: a source/variant identifier,
observed and available times, and the boolean assertion that the original
alert-enabled branch was active. The assertion must be available at or before
the anchor and match the selected source variant. Missing, stale, contradictory
or mismatched activation evidence means `OBSERVE_ONLY`: the candidate remains
in the ledger but no `tracker.record()` call is made.

### 2. Outer-pass source binding

Before runtime wiring, an intake/audit module must map the retained source's
outer market-watch pass into an ordered projection: initial watch-state load,
pre-producer save, producer calls, selection/arbitration, tracker recording,
final watch-state save, and tracker lifecycle placement.  The mapping pins the
same retained source commit/blob model used by existing source auditors and
fails closed if the original source changes or a required call cannot be
projected.

This is not permission to merge source variants or to declare that every
producer is replayable.  The projection records which source calls are wired
to the internal-reversal path and which remain unsupported.  It also establishes
the legal lifecycle position relative to candidate admission; that order may
not be chosen by this design.

### 3. Stateful pass execution

One `ReplayClock` is owned by a run.  At each anchor the runner applies all
earlier/equal publications in sequence, advances the clock to `T`, and builds
the provider objects at that same clock.  `CausalWatchStorage` retains watch
state; `CausalAdmissionContext` retains tracker/artifact/lock evidence; the
accepted producer evaluates only its supplied as-of frames. The selected plan
is handed to the source-faithful tracker path only when the anchor's accepted
activation evidence permits it; it is never reconstructed from a serialized
candidate. In `OBSERVE_ONLY`, it is preserved as a selected candidate and the
pass records why tracker registration did not occur. During this first slice,
all newly selected candidates are `OBSERVE_ONLY` because the complete outer
admission gate is not yet a source-audited replay component. Existing supplied
tracker records still flow through the accepted closed lifecycle resolver.

For each legal closed lifecycle pass, the runner invokes
`TrackerLifecycleCaller.check(...)` with `LifecycleClosedResolver.resolve` and
the pass epoch.  The existing caller remains the only owner of its gate/save
sequence.  The resolver remains the only owner of the accepted record-local
closed-bar Pending/Open transition order.  A missing, stale, unverified or
unsupported evidence dependency creates a pass diagnostic and preserves the
source component's own skip/block behavior; it never becomes an invented loss.

### 4. Ledger and checkpoint

`ReplayRunLedger` is append-only in run order.  A pass produces a
`ReplayPassRecord` containing: run/pass IDs; decision time; consumed event IDs;
watch/tracker input and output fingerprints; producer and tree diagnostics;
candidate/plan IDs when source-selected; lifecycle messages and raw state
transition IDs; blocked/unsupported reasons; and detached traces.

No ledger field is named `success`, `failure`, `net_R`, or `net_pnl` in this
subsystem.  A terminal source state may be recorded as a raw fact, but cannot
be interpreted as a learning label here.

`ReplayCheckpoint` contains the run identity, last consumed schedule key,
clock, serialized watch/tracker state, pass index, ledger hash and source-pin
fingerprints.  It does not contain mutable references to provider objects or
unbounded raw frames.  Resume rejects a mismatch in bundle identity, source
pin, event order, initial artifact identity, or previous ledger hash.  The
runner must prove split-run equivalence against an uninterrupted run.

### 5. Failure handling and safety

- Invalid structural inputs fail before the first pass.
- A failure in one candidate/lifecycle record follows the accepted local
  resolver behavior; an impossible scheduler/checkpoint invariant stops the
  run with a machine-readable run-level blocker.
- `BLOCKED`, `SKIPPED`, `NO_CANDIDATE`, and `UNSUPPORTED` remain distinct in
  the ledger and in test expectations.
- The implementation has no network, filesystem discovery, broker, data-vendor
  or original-source execution capability.  Retained source is parsed only.
- Every public report continues to expose `ready_for_replay=false` and
  `ready_for_training=false` until this vertical slice has independent
  acceptance.  Even after acceptance, it will not claim training readiness.

### 6. Event-to-provider evidence binding

The evidence bundle is not merely a schedule.  A supplied event that drives a
runtime provider must be cryptographically tied to the exact artifact that the
provider consumes.  Otherwise an operator could change an event payload while
leaving its ID and time intact, and the replay ledger would falsely attest to
the same historical decision.

For this first slice, an event payload may contain an explicit
`evidence_binding` with exactly these fields:

- `consumer`: `ADMISSION_PUBLICATION` or `INTERNAL_REVERSAL_INPUT`.
- `artifact_id`: the exact publication ID or replay pass ID respectively.
- `artifact_digest`: lowercase SHA-256 of the canonical supplied artifact.

At each pass, before advancing the shared clock, the runner calculates the
canonical digest of the supplied `InternalReversalInputs` for that pass and of
every `CausalAdmissionContext` publication whose `available_at` is at or before
the pass anchor.  It requires a unique, eligible event binding with the same
consumer, artifact ID, artifact digest and, for publications, availability and
kind/channel identity.  Initial watch/admission seeds remain covered by the
separately retained Task 3 provider-baseline fingerprint, which is committed in
every ledger record.  Derived state is covered by the linked prior record.

An unmatched, duplicate, future, or payload-digest-mismatched binding emits
`BLOCKED` before the context advances, lifecycle runs, or producer runs.  The
runner does not infer bindings from similar IDs, event kinds, timestamps, or
content.  It never applies a future provider-publication prefix.

Each pass record stores a canonical commitment for every event available to
that pass: event ID, availability, sequence, full payload digest, and any
declared evidence-binding fields.  This makes a same-ID/same-time payload
substitution observable in both the record and linked ledger digest even where
the event is diagnostic rather than a provider input.

## Interfaces and file boundaries

The implementation plan will use focused modules under
`trading_system/tree_replay/`:

- `causal_replay_contracts.py`: frozen input, schedule, ledger and checkpoint
  types plus validation and canonical hashing.
- `causal_replay_source.py`: retained-source outer-pass intake/audit projection;
  static only, no runtime source import.
- `causal_replay.py`: clock-driven runner and source-ordered adapter.
- `causal_replay_checkpoint.py`: checkpoint serialization/restore and identity
  validation, separated from orchestration.
- `tests/tree_replay/test_causal_replay_*.py`: behavioral and split-run tests.
- `tests/tree_spec/test_causal_replay_source.py` and a CLI source checker:
  mutation-resistant source-order proof.
- `docs/architecture/CAUSAL-REPLAY-USAGE.md`: public contract, limitations and
  verification commands.

Existing verified modules are dependencies; they are not refactored merely to
fit the new runner.

## Required verification

The implementation is accepted only when all of the following are demonstrated
with synthetic, explicit evidence:

1. Future or unavailable bars/publications cannot change an earlier pass.
2. Equal-time ordering follows supplied sequence, never incidental iteration.
3. An internal-reversal selected plan reaches the tracker through the approved
   private handoff only after a later source-audited outer-admission binding.
   In this slice, it remains an observed candidate regardless of activation
   evidence; a refused/no-candidate/blocked producer never creates an admitted
   trade.
4. The closed lifecycle sees only post-send/post-fill bars through the accepted
   resolver and cannot convert raw movement facts into P&L labels.
5. Watch and tracker changes persist across legal passes in source-projected
   order; no state changes after a failed pass are fabricated.
6. An uninterrupted run and all tested legal checkpoint/resume splits produce
   identical ordered ledgers and final state fingerprints.
7. Unsupported producer/pass identities are explicit and do not silently
   disappear or produce substitutes.
8. Missing, future, stale, contradictory or source-mismatched tracker-activation
   evidence cannot create a tracker record; valid evidence is retained only as
   an observation until the outer-admission binding exists.
9. Activation evidence cannot override the missing outer-admission binding or
   create a new tracker row in this first slice.
10. Source-audit mutations to outer ordering, source pins, required calls or
   readiness flags fail closed.
11. Existing component suites remain green; no test permits live I/O or imports
    the retained source checkout.
12. Changing the payload of a same-ID/same-time bound event blocks the pass or
    changes its record/ledger commitment; a future bound event cannot affect an
    earlier pass; and a legal checkpoint/resume split remains identical after
    event-to-provider binding is enforced.

## Completion definition for this slice

This slice is complete only when a deterministic, source-audited closed-bar
run over supplied evidence can produce a raw, resumable ledger for the supported
internal-reversal path and its tracker lifecycle, with all required checks above.
It is still not an outcome dataset or an economic simulation.  The next design
after acceptance is the economic execution/label contract, which requires
explicit decisions on instrument-aware costs, fill rules, time exit, ambiguity,
and censoring before any historical P&L labels are generated.

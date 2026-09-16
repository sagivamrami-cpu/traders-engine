# Outer Admission Causal Binding Design

## Status and objective

This is the next bounded replay subsystem after the accepted closed-bar causal
replay slice. It binds the source outer market-watch admission order for one
already supported `level_reversal:5m` candidate to supplied, time-valid evidence.
Its purpose is to distinguish a source-admitted tracker row from an observed
candidate. It does **not** infer a broker fill, economic exit, P&L, management
action, dataset label, model score, delivery or live order.

The approved fixed-full-TP1 economic control remains a later simulation policy.
The dynamic-management workstream remains separate and is still dependent on
the J1/J2 decisions.

## Source basis

- `docs/architecture/MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md`
- `docs/architecture/TRACKER-ADMISSION-SOURCE-CONTRACT.md`
- `docs/superpowers/specs/2026-09-15-closed-bar-causal-replay-design.md`
- Pinned `chart-desk` commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.

The source order for reversal is preserved: annotate entry quality (non-veto),
validate plan, hunting window, entry-clock, post-stop cooldown, occupied slot,
same-level cooldown, active-reversal/episode treatment, then tracker recording
when the source alert-recording branch is evidenced as enabled. Each source
gate keeps its distinct missing/error behavior; no new threshold or unified
“quality” veto is introduced.

## Boundary

### Included

- An immutable, causal admission-evidence contract with identity, availability,
  sequence and canonical digest commitments for every input consumed by an
  outer-admission pass.
- A narrow offline provider that exposes only source-required tracker state,
  full ordered watch-log prefix, frames/quotes and source-local clock inputs.
- A source-order admission adapter for the level-reversal path. It returns an
  explicit source admission decision or reason, plus detached annotations.
- Source-faithful tracker registration through the existing offline
  `TrackerAdmission` port only after all prior outer gates permit it and the
  `TrackerActivationEvidence` is `EVIDENCED_ENABLED`.
- Replay ledger/checkpoint records that differentiate `OBSERVE_ONLY`, rejected
  admission, admission failure, and a tracker row registered by source logic.
- Tests for chronology, no future publication, exact gate order, no duplicate
  registration, persistence/checkpoint equivalence and no delivery/economics.

### Excluded

- Any broker state, order, fill, quantity, stop, TP, partial, BE, trailing,
  economic label or portfolio calculation.
- Telegram, customer publication, outbox delivery, files from a live host or
  runtime source imports.
- Other producers and cross-producer policy generalization.
- Replacement of the source byte-tail log behavior with semantic rejection rows.
- Treating an admitted advisory row, including source `OPEN`, as a verified
  filled position. `born_open` and `revalidation_verified` retain their source
  meanings only.

## Design

### 1. Admission evidence

Each pass carries an immutable `OuterAdmissionInputs` object and a one-to-one
event binding. It names the source variant, candidate plan fingerprint,
watch-state seed, tracker-state seed, full byte-exact watch-log prefix, quote
and frame publications, and source local-time/calendar evidence. Every artifact
has `observed_at`, `available_at`, `covered_through`, source identity and digest.

The adapter receives only evidence published at or before its pass time. It
never reads a current file, wall clock, local timezone setting or live source
module. Required input binding failures block before watch/tracker mutation.

For a source branch that catches a missing optional dependency and continues,
the adapter preserves the original result and appends a diagnostic. It must not
replace the source's behavior with a hidden fail-open or fail-closed rule.

### 2. Admission result

`OuterAdmissionDecision` is a detached record with:

- `status`: `ADMITTED_TRACKER`, `REJECTED`, `OBSERVE_ONLY`, `BLOCKED`, or
  `UNSUPPORTED`;
- ordered gate trace, one reason per stopping gate;
- source annotations such as entry-quality and cooldown-release evidence;
- exact tracker identity/row fingerprint only when registration succeeded;
- causal input commitments and no economic fields.

`ADMITTED_TRACKER` means only that source tracker recording returned true against
the supplied offline state. It does not mean an executed trade.

### 3. Source-order adapter

The adapter owns orchestration, not duplicate strategy math. Existing audited
vendor helpers remain the owners of `hunting`, entry-clock, `has_open`,
`blocked_after_stop`, `blocked_same_level` and `record`. The adapter passes the
actual source-selected `Plan` through internally; it never recreates a plan from
the public serialized candidate.

Heterogeneous watch state and save ordering are preserved: load, source
pre-producer save, source-admission effects, final save. Tracker admission owns
its independent lock/load/save sequence. Duplicate episode effects and
active-reversal behavior are explicitly represented rather than normalized.

### 4. Causal replay integration

`ClosedBarCausalReplay` continues to run lifecycle first in its accepted place.
For a selected reversal candidate, it invokes outer admission only when its
dedicated input is correctly bound and the anchor activation is
`EVIDENCED_ENABLED`. Disabled/future/mismatched activation stays `OBSERVE_ONLY`.
An admission rejection is a replay diagnostic, not a losing trade.

The public ledger may record the admitted tracker identity and state fingerprint,
but not raw log/frame payloads. Checkpoint restore validates all admission input
commitments and produces the same ledger digest as a one-shot run.

## Safety invariants

1. A pass cannot consume future or unbound admission evidence.
2. Source gate order is observable and mutation-tested.
3. A candidate rejected, blocked, or observed **before the record gate** cannot
   call `TrackerAdmission.record`. A persistence failure raised by that gate is
   a distinct post-attempt `BLOCKED` result (`TRACKER_RECORD_FAILED`), matching
   the source `try/except`; it has no tracker identity, watch-episode write, or
   admitted state.
4. A successful registration is idempotent across replay resume and duplicate
   anchors; it cannot create two tracker rows for one source geometry.
5. Tracker recording and lifecycle transitions remain advisory-state facts; no
   economic outcome fields exist in this boundary.
6. Raw log payloads, market data and external side effects never enter the
   public ledger or filesystem.
7. All public replay/training readiness flags remain false.

## Acceptance evidence

Acceptance requires focused red/green tests, mutation/source-order audit against
the pinned source, checkpoint equivalence, source-root CLI verification, and an
independent review. It must explicitly demonstrate that no path sends delivery,
creates a broker artifact, claims a fill, emits economics or promotes training
readiness.

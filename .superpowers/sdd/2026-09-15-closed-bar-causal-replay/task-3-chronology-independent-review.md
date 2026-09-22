# Task 3 chronology correction — final adversarial independent re-review

Status: CHANGES_REQUESTED

## Scope and method

Read-only static review of Task 3 in
`docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`, the replay
design, all preceding Task 3 reports and independent reviews, and the current
checkpoint/context/clock implementation and tests. No implementation or test
was edited, no subagent was used, no commit was made, and no retained source,
test, or project code was executed.

## Correction verified

The reported I2 provider-evidence backdate is corrected in the current code.
After exact trusted-suffix matching derives the consumed publication and lock
prefixes, `ReplayProviderBaseline._matches_checkpoint()` rejects when either:

- a consumed publication has `available_at > decision_time`
  (`causal_replay_checkpoint.py:83-87`); or
- a consumed lock step has either `started_at > decision_time` or
  `completed_at > decision_time` (`causal_replay_checkpoint.py:88-90`).

Restore supplies the parsed, bound checkpoint clock to that matcher only after
outer checksum, bundle, ledger, index, and watch/admission clock agreement
checks (`causal_replay_checkpoint.py:169-197`). Therefore a checksum recomputed
image backdated before a consumed publication or before either boundary of a
consumed lock step fails the trusted-baseline check. A valid checkpoint remains
restorable through the normal `checkpoint()` / `restore_checkpoint()` path in
`tests/tree_replay/test_causal_replay_checkpoint.py:59-77`.

The new regression at `tests/tree_replay/test_causal_replay_checkpoint.py:168-180`
does recompute both nested and outer checksums after backdating all three clock
surfaces. Its fixture consumes a publication and a zero-duration lock sequence
at `T + 2s` (`:225-239`), so the publication branch proves rejection. The code
also contains the independent lock predicate above, but the regression combines
both evidence classes; a later test should isolate a consumed-lock-only
backdate so removal of the lock predicate cannot be masked by the publication
predicate.

## Blocking finding

### Critical C1 — a checkpoint can still rewind before a completed ledger/pass anchor

Task 3 binds each completed ledger row to the same indexed bundle anchor and
its full available-event prefix, but it never requires the checkpoint clock to
be at or after the last completed record's `decision_time`.

- `_validate_ledger_prefix()` checks only `pass_id`, `decision_time`, and
  consumed event IDs (`causal_replay_checkpoint.py:234-241`).
- `checkpoint_from()` obtains `at = admission.decision_time` after that check,
  but does not compare `at` to any completed ledger record (`:144-157`).
- `restore_checkpoint()` repeats the ledger-prefix validation, parses the
  checkpoint time, and binds the supplied clock, again with no such comparison
  (`:178-197`).

The existing ordinary fixture makes the inconsistency concrete:
`ledger()` contains record 0 at `T + 1s`
(`tests/tree_replay/test_causal_replay_checkpoint.py:46-51`), while the
provider baseline can have no publications or locks. Build that otherwise-valid
checkpoint, replace only outer `clock_time`, admission `decision_time`, and
watch `observed_at`/`available_at` with `T`, recompute the nested and outer
canonical checksums, and restore with `ReplayClock(T)`. Every present check
passes: the ledger still matches its bundle anchor; watch and admission agree
with the new clock; and an empty provider schedule supplies no consumed
publication/lock to trip the new I2 guard. The result has `next_pass_index ==
1` and a ledger claiming a pass at `T + 1s`, but its shared replay clock is at
`T`.

This violates the design's monotonic single-clock execution rule and a legal
resume state: a completed pass cannot exist at a future decision time relative
to the checkpoint clock. It also leaves the checkpoint factory itself able to
create that invalid state directly from a ledger at `T + 1s` and providers
still at `T`.

Required correction:

1. At checkpoint creation and restore, reject a nonempty ledger when the shared
   checkpoint time is earlier than its last completed record/anchor decision
   time (prefer comparing against the immutable indexed anchor after prefix
   validation).
2. Add a checksum-recomputed restore regression with no provider publications
   or lock steps, and a direct factory regression, each attempting that
   pre-anchor backdate.
3. Split the current I2 regression into publication-only and lock-only cases,
   retaining a valid restore assertion for each legal consumed-evidence image.

## Prior Task 3 invariants rechecked

- Indexed ledger/bundle anchor and full event-prefix binding remain enforced at
  creation and restore (`causal_replay_checkpoint.py:144, 181, 234-241`).
- The independently retained provider baseline still binds source identities,
  current provider images, and exact publication/lock suffixes (`:43-102`),
  preventing checksum-recomputed schedule/source substitution.
- Checkpoint creation still requires the identical watch/admission clock object
  (`:142-143`), while restore binds both reconstructed providers to the one
  supplied exact `ReplayClock` (`:182-200`).
- Both checkpoint and packed snapshot parsers reject extended and basic ISO
  timestamp fractions longer than six digits before parsing
  (`causal_replay_checkpoint.py:255-264`, `admission_context.py:463-472`);
  checksum-recomputed regressions cover both spellings.
- Snapshot restore still rejects remaining publications at/before the restored
  clock and remaining lock steps started before it
  (`admission_context.py:381-384`).
- The reviewed paths add no runner, retained-source execution, tracker record,
  delivery, economic label, dataset/training/model behavior, or readiness-true
  claim. `CausalAdmissionContext.report()` continues to expose both readiness
  flags as false (`admission_context.py:399-404`).

## Verification note

No commands that import or execute project source were run, as required. The
test-pass counts in earlier implementation reports are historical evidence
only, not fresh verification for this review.

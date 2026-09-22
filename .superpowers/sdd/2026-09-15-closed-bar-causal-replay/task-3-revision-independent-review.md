# Task 3 corrective revision independent review

Status: CHANGES_REQUESTED

## Scope reviewed

Corrected Task 3 checkpoint/context implementation only: the Task 3 plan and
design, initial review, corrective report, current
`admission_context.py`, `causal_replay_checkpoint.py`, and the complete Task 3
checkpoint/admission-context/shared-clock tests. This review made no runtime
edits, invoked no subagents, and did not execute or import retained source.

## Critical

None.

## Important

### I1 — basic ISO timestamps with more than six fractional digits still bypass both restore guards

`_time()` only recognizes an extended ISO date/time before calling
`datetime.fromisoformat()` at
`trading_system/tree_replay/causal_replay_checkpoint.py:255-264`; `_parse_time()`
uses the equivalent extended-only pattern at
`trading_system/tree_replay/admission_context.py:463-472`. Python accepts the
basic ISO forms `20260909T160100.0000000+0000` and
`20260909T160500.0000000+0000`, silently truncating their seventh fractional
digit. They do not match either guard's `YYYY-MM-DD...` regular expression.

Independent checksum-recomputed probes both restored successfully:

```text
outer accepted: 2026-09-09T16:01:00+00:00
packed accepted: 2026-09-09T16:05:00+00:00
```

The outer probe changed only checkpoint `watch.covered_through` to
`20260909T160100.0000000+0000` and recomputed the outer canonical checksum. The
packed probe changed only
`admission.state.quotes.fields.covered_through.value` to
`20260909T160500.0000000+0000`, recomputed the nested snapshot checksum and
then the outer checkpoint checksum. Both values are semantically equal to the
trusted baseline after truncation, so baseline matching does not mask this
parser failure.

This leaves the former over-precision issue open for valid basic ISO input,
contrary to the corrective requirement to reject fractional precision beyond
six for every outer and packed snapshot/checkpoint timestamp. Reject a
fractional component longer than six independent of extended/basic ISO spelling,
and add checksum-recomputed outer and packed basic-form regressions.

## Minor

None.

## Former-issue adjudication

- **Indexed ledger/bundle-anchor and event-prefix binding — closed.**
  `checkpoint_from()` invokes `_validate_ledger_prefix()` before serialization
  (`causal_replay_checkpoint.py:124-151`), and `restore_checkpoint()` invokes
  it again after rebuilding the ledger (`:169-175`). The validator requires
  each indexed record's pass ID and decision time to equal the corresponding
  immutable anchor and its consumed IDs to equal the full ordered
  `events_before_or_at(anchor.decision_time)` prefix (`:227-234`). The creation
  and checksum-recomputed restore regressions are at
  `test_causal_replay_checkpoint.py:98-127`.
- **Independently retained provider baseline — closed.**
  `ReplayProviderBaseline.capture()` stores detached original watch and
  admission provider evidence (`causal_replay_checkpoint.py:46-55`), while a
  checkpoint carries only its fingerprint (`:145-151`). Restore compares the
  reconstructed provider seeds, frame image, and exact remaining publication
  and lock suffixes to that independently supplied baseline (`:67-102`,
  `:165-189`). Checksum-recomputed forged watch-source, future-publication
  substitution/addition, and future-lock substitution tests are at
  `test_causal_replay_checkpoint.py:130-165`.
- **Exact same clock object at creation — closed.** `checkpoint_from()` rejects
  different clock instances by identity, not time equality
  (`causal_replay_checkpoint.py:132-138`); the negative test is at
  `test_causal_replay_checkpoint.py:168-178`.
- **Submicrosecond serialized timestamps — only partially closed.** Extended
  ISO strings are rejected and have direct tests at
  `test_causal_replay_checkpoint.py:181-186` and
  `test_admission_context.py:365-373`; I1 shows basic ISO values remain
  accepted.
- **No prohibited side effect or readiness claim — confirmed.** The reviewed
  checkpoint/context paths only validate, serialize, and reconstruct supplied
  providers; they contain no tracker-record, delivery, economic, dataset,
  training, model, retained-source, or live-operation path. Public context
  reporting still sets both readiness flags false at
  `admission_context.py:399-404`.

## Verification run

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
181 passed in 14.08s
```

The focused suite confirms the corrected extended-ISO cases and all other
former issue regressions. It does not cover the basic ISO bypass above.

## Recommended next action

Fix I1 and add outer and packed basic-ISO checksum-recomputed regression tests;
then rerun the same five-suite command before asking for re-review.

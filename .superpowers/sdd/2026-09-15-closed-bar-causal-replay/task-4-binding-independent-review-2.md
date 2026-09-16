# Task 4 Independent Review 2 — Revised Evidence Binding

## Verdict

CHANGES_REQUESTED

## Scope and method

Read-only independent acceptance review of the supplied design, Task 4 brief,
prior independent review, and revised binding report; current
`causal_replay_contracts.py`, `causal_replay.py`, `admission_context.py`, and
the three requested focused test modules. No retained source was read, imported,
compiled, or executed. No implementation or test was changed, no subagent was
called, and no commit was created.

Focused verification passed:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
136 passed in 7.57s
```

## Finding

### Critical — `required_event_ids` can be satisfied by an unrelated eligible event while a different event binds the exact pass input

`ClosedBarCausalReplay._validate_bound_evidence()` checks only that every ID in
`anchor.required_event_ids` exists and is no later than the anchor
(`causal_replay.py:290-293`). It then separately scans *all* eligible events for
one `INTERNAL_REVERSAL_INPUT` binding whose `artifact_id` equals the pass ID
(`:295-307`). There is no assertion that the unique matching binding event is
one of the required IDs, nor that each required event has that exact binding.

This violates the Task 4 brief requirement that every required event ID have an
exact matching internal-reversal-input binding for the pass input, and the
design's pre-advance proof for the exact pass input. It allows the pass to
consume a required event which is merely available and unrelated, while a
non-required eligible event provides the actual input binding.

Independent in-memory probe, using only current replay modules and synthetic
test fixtures, constructed at the same anchor time:

```text
required_event_ids = ('required-unrelated',)
event 'required-unrelated' = eligible, unbound, unrelated payload
event 'input-binding' = eligible, non-required, valid INTERNAL_REVERSAL_INPUT
                         binding for pass-0 and the exact supplied input digest
result.outcome = NO_CANDIDATE
result.consumed_event_ids = ('required-unrelated', 'input-binding')
```

The expected result is `BLOCKED` before `admission.advance_to()`, watch access,
lifecycle resolution, or producer evaluation. The actual `NO_CANDIDATE` proves
the unrelated-ID bypass.

Required correction: bind each `required_event_id` directly to its expected
consumer, artifact ID, and artifact digest (for this pass, the exact
`INTERNAL_REVERSAL_INPUT` binding) and reject missing, duplicate, future, or
unrelated required bindings before any provider advance. If the contract intends
additional required event classes, encode that expected relation explicitly;
availability alone cannot establish it.

Required regression test: create two eligible events exactly as in the probe —
an unbound/unrelated required event and a separate non-required valid input
binding — and assert `BLOCKED`, empty watch trace, zero consumed admission
publications, and no producer call. Also cover the inverse mapping where a
required event binds a different pass ID.

## Verified revised boundaries

- The ledger now commits each time-eligible event's ID, availability, sequence,
  full canonical payload digest, and declared binding without retaining raw
  payload (`causal_replay_contracts.py:247-253`, `:264-300`; runner
  `causal_replay.py:235-252`). The provider-baseline fingerprint is included in
  every appended record and is record-digest-covered through diagnostics.
- Before `admission.advance_to()`, due admission publications require one
  eligible binding with exact publication ID, kind/channel mapping,
  availability, and canonical artifact digest (`causal_replay.py:311-318`,
  then advance at `:340-344`). Duplicate or digest-mismatched bindings for the
  same artifact fail closed through `unique_binding()`.
- The schedule view is read-only (`admission_context.py:234-237`), and the
  focused split/resume test remains green (`test_causal_replay.py:263-277`).
- No new candidate path calls `TrackerAdmission.record`: the runner contains no
  `record` call and the focused test patches it to fail (`test_causal_replay.py:135-150`).
  The runner's lifecycle tape is memory-only; no external I/O, economics,
  dataset/training/model path, or readiness claim was introduced.

The critical bypass above prevents acceptance despite those retained controls.

## Finding count

- Critical: 1
- High: 0
- Medium: 0
- Low: 0

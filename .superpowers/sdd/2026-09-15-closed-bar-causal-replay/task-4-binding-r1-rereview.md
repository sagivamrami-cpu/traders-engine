# Task 4 Binding Fix Round 1 Re-review

## Verdict

ACCEPTED

## Scope and method

Read-only, scoped re-review of the Task 4 evidence-binding fix. Read the
required project/exchange guidance, closed-bar replay design, Task 4 brief,
prior independent review, and revised implementation report. Inspected the
current replay runner, contract/context boundaries, and focused replay tests.
No retained source was read, imported, compiled, or executed. No code/test was
changed, no subagent was used, and no commit was created.

Focused synthetic verification passed:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py::test_required_event_cannot_be_substituted_by_a_nonrequired_internal_input_binding tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider
22 passed in 3.80s
```

## Prior finding

### Critical — required event could be substituted by a non-required valid input binding

ADDRESSED.

The runner now makes the current single internal-reversal input relation
explicit before any stateful operation. It rejects any anchor whose
`required_event_ids` does not contain exactly one ID
(`causal_replay.py:292-293`), obtains that required event, and requires that
event itself to be time-eligible and bound to `INTERNAL_REVERSAL_INPUT`, the
current `pass_id`, and the canonical digest of this pass's supplied
`InternalReversalInputs` (`:294-303`). It then requires the globally unique
eligible binding for that consumer/artifact and proves it is the same required
event with the same digest (`:305-322`).

Consequently, both prior bypass forms fail closed: an unbound required event
plus a non-required valid input event fails the direct required-binding check;
a required event bound to `pass-1` plus a non-required valid `pass-0` event
does the same. The regression parametrizes both forms and asserts `BLOCKED`,
no producer call, empty watch trace, and zero consumed admission publications
(`test_causal_replay.py:206-243`). The focused execution above passed both
cases.

The proof remains before `admission.advance_to()` (`causal_replay.py:347-354`),
and therefore before watch load/save, lifecycle resolution, and producer
evaluation. This closes the prior pre-advance bypass.

## Retained binding guarantees

- The exact-one-required-event rule is coherent with the current Task 4 design:
  one `InternalReversalInputs` object is mapped to each exact pass ID. It fails
  closed for zero or multiple required IDs rather than letting an unrelated
  event establish that single input proof.
- Admission-publication validation remains a separate exact, unique proof for
  each due publication, retaining kind/channel, availability, ID, and artifact
  digest checks (`causal_replay.py:324-331`).
- Every time-eligible event still produces an immutable full-payload commitment
  in every record, and the Task 3 provider-baseline fingerprint remains in the
  record diagnostic before the record digest is calculated
  (`causal_replay.py:235-252`; `causal_replay_contracts.py:444-500`).
- The condition is pure validation before context mutation. The existing
  one-shot versus split/resume digest-equivalence test remains present
  (`test_causal_replay.py:303-317`) and passed as part of the full focused
  module run.

## New breakage in fix scope

None found.

## Finding count

- Addressed: 1
- Open: 0
- New Critical/Important: 0

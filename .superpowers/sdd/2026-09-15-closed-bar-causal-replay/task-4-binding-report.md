# Task 4 Revised Evidence-Binding Report

## Scope

Implemented only the revised closed-bar evidence-binding correction in the
assigned replay contracts, replay runner, admission-context schedule view, and
their focused tests. No source checkout was read, imported, compiled, or
executed. No broker, delivery, network, retained raw-data write, economic
label, dataset, training, model, readiness, or new `TrackerAdmission.record`
path was introduced.

## Changes

- Added `ReplayEventCommitment`, `ReplayEvent.commitment()`, and strict
  all-or-nothing `evidence_binding` validation. A binding is exactly
  `consumer`, `artifact_id`, and `artifact_digest`; supported consumers are
  `ADMISSION_PUBLICATION` and `INTERNAL_REVERSAL_INPUT`.
- Added deterministic `canonical_evidence_digest()` for supplied provider
  artifacts. It structurally covers nested dataclasses, aware datetimes,
  tuples, lists, mappings, scalar values, and concrete dataclass type names;
  it does not use `repr()` or object identity.
- Added the read-only `CausalAdmissionContext.replay_publications_through()`
  schedule view. It neither advances the shared clock nor consumes a provider
  publication.
- Changed the runner to verify required event availability, exactly one bound
  internal reversal input for the pass, and exactly one matching event for each
  due admission publication before `admission.advance_to()`. Publication
  verification includes the event kind mapped from the publication channel,
  exact availability, artifact ID, and canonical artifact digest.
- Every replay record now carries all time-eligible immutable event
  commitments, including event ID, availability, sequence, full canonical
  payload digest, and optional binding, plus the retained provider-baseline
  fingerprint. This metadata is stored as a canonical record diagnostic so the
  existing checkpoint serializer/restorer retains it without an out-of-scope
  checkpoint module edit. Typed `ReplayPassRecord` properties expose it as
  `consumed_event_commitments` and `provider_baseline_fingerprint`. Raw event
  payloads remain absent from the ledger.
- Updated ordinary replay fixtures to provide valid internal-reversal bindings.
  Added adversarial coverage for changed bindings, future bindings, missing,
  mismatched, and duplicate publication bindings, ledger commitment fields,
  split/resume identity, schedule-view immutability, and null/partial bindings.

## RED/GREEN evidence

### Binding API and causal verification cycle

RED command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

RED output: collection failed as expected because
`canonical_evidence_digest` and `ReplayEventCommitment` did not yet exist
(`2 errors in 1.60s`). The tests named the missing binding API and did not
exercise implementation code that already provided the behavior.

Initial implementation run exposed a ledger serialization defect rather than a
binding-test false positive: ISO commitment timestamps were reconstructed as
strings while the typed contract requires aware datetimes (`16 failed, 119
passed`). The reconstruction was normalized to parse its own canonical ISO
form.

GREEN command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

GREEN output:

```text
135 passed in 22.17s
```

### Explicit-null binding fail-closed cycle

RED command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py::test_event_binding_is_all_or_nothing_and_has_exact_fields -q --tb=short -p no:cacheprovider
```

RED output: `evidence_binding: null` was accepted (`1 failed, 4 passed in
5.25s`), proving the explicit-present/null edge was not fail-closed.

GREEN command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py::test_event_binding_is_all_or_nothing_and_has_exact_fields -q --tb=short -p no:cacheprovider
```

GREEN output:

```text
5 passed in 3.74s
```

Final focused command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

Final focused output:

```text
136 passed in 7.43s
```

Required dependency command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider
```

Required dependency output:

```text
180 passed in 30.40s
```

`git diff --check` over the scoped files emitted no whitespace errors.

## Remaining concerns

- This is an offline supplied-evidence proof and observation ledger only. The
  baseline fingerprint remains an external Task 3 retention trust anchor;
  committing it does not turn it into a feed or persistence certification.
- The change intentionally leaves all outer admission, tracker creation,
  delivery, execution, economics, replay-data coverage, dataset, training,
  model, and live-trading work outside this component.

## Fix round 1

### Finding and root cause

The independent reproduction was confirmed. The runner previously verified
`required_event_ids` only for time eligibility, then found the pass input by
scanning all eligible events. An eligible non-required event could therefore
supply the valid `INTERNAL_REVERSAL_INPUT` binding while the required event was
unbound or bound to a different pass.

The fix makes the one required event itself the exact pass input proof: it must
be eligible and bind `INTERNAL_REVERSAL_INPUT`, the current pass ID, and the
canonical digest of the supplied `InternalReversalInputs`. It also requires
exactly one required ID and requires the globally unique matching input binding
to be that same event. Thus an unbound/wrong required event, a future required
event, a second required ID, or a non-required duplicate cannot satisfy or
substitute for the pass input. All validation remains before context advance,
watch access, lifecycle resolution, and producer evaluation.

### RED/GREEN evidence

RED command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py::test_required_event_cannot_be_substituted_by_a_nonrequired_internal_input_binding -q --tb=short -p no:cacheprovider
```

RED output:

```text
2 failed in 1.78s
```

Both independently meaningful cases produced `NO_CANDIDATE` instead of
`BLOCKED`: (1) an eligible unbound required event plus an eligible non-required
valid pass-input binding, and (2) a required event bound to `pass-1` plus the
same non-required valid `pass-0` binding. The tests also require no producer
call, no watch trace, and no admission publication consumption when blocked.

GREEN command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py::test_required_event_cannot_be_substituted_by_a_nonrequired_internal_input_binding -q --tb=short -p no:cacheprovider
```

GREEN output:

```text
2 passed in 4.08s
```

Focused verification command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

Focused verification output:

```text
138 passed in 24.52s
```

Dependency verification command:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider
```

Dependency verification output:

```text
182 passed in 25.66s
```

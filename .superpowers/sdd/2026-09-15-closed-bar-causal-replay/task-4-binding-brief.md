### Task 4: Closed-bar replay runner and raw observation ledger

**Files:**
- Create: `trading_system/tree_replay/causal_replay.py`
- Create: `tests/tree_replay/test_causal_replay.py`
- Modify: `trading_system/tree_replay/__init__.py`

**Interfaces:**
- `ReplayEvent.payload["evidence_binding"]`, when present, is the exact JSON
  object `{consumer, artifact_id, artifact_digest}`.  Consumers are only
  `ADMISSION_PUBLICATION` and `INTERNAL_REVERSAL_INPUT`; no partial or inferred
  binding is accepted.
- `ReplayEvent.commitment() -> ReplayEventCommitment` returns immutable event
  identity, availability, sequence, canonical full-payload digest and optional
  exact evidence binding.  `ReplayPassRecord.consumed_event_commitments` holds
  those commitments rather than IDs alone, and
  `provider_baseline_fingerprint` commits the Task 3 retained baseline.
- `CausalAdmissionContext.replay_publications_through(at) -> tuple[Publication, ...]`
  is a read-only, exact ordered provider schedule view; it does not advance the
  clock or mutate provider indexes.
- `ClosedBarCausalReplay(bundle, *, clock, watch, admission, reversal_inputs).run() -> ReplayRunLedger`.
- `reversal_inputs: Mapping[str, InternalReversalInputs]` maps exact pass IDs to `snapshot_id`, `map_requests` and `reversal_requests`; missing input produces `BLOCKED`, never a fallback.
- `run_until(pass_count: int) -> tuple[ReplayRunLedger, dict]` executes a prefix and returns a canonical checkpoint through Task 3.
- New selected plans remain `OBSERVE_ONLY`; no runtime path invokes `admission.tracker.record`.

- [ ] **Step 1: Write failing replay behavior tests**

```python
def test_run_advances_shared_clock_and_keeps_new_selected_plan_observe_only(monkeypatch):
    replay = make_replay(two_anchor_bundle())
    ledger = replay.run()
    assert [row.outcome for row in ledger.records] == ["OBSERVE_ONLY", "NO_CANDIDATE"]
    assert ledger.records[0].candidate["source_plan"] is not None
    assert record_calls() == []

def test_future_publication_cannot_change_previous_pass_or_lifecycle(monkeypatch):
    baseline = make_replay(bundle_with_future_bar()).run()
    changed = make_replay(bundle_with_changed_future_bar()).run_until(1)[0]
    assert baseline.records[0].digest == changed.records[0].digest

def test_same_event_identity_with_changed_bound_payload_blocks_before_provider_use(monkeypatch):
    replay = make_replay(bundle_with_bound_reversal_input())
    changed = make_replay(bundle_with_same_id_time_but_changed_binding_digest())
    assert replay.run().records[0].outcome == "NO_CANDIDATE"
    assert changed.run().records[0].outcome == "BLOCKED"
    assert changed.watch.trace == []

def test_each_record_commits_event_payload_and_provider_binding(monkeypatch):
    record = make_replay(bundle_with_bound_reversal_input()).run().records[0]
    commitment = record.consumed_event_commitments[0]
    assert commitment.payload_digest == canonical_digest(bundle.events[0].payload)
    assert commitment.consumer == "INTERNAL_REVERSAL_INPUT"
    assert commitment.artifact_id == record.pass_id

def test_split_run_matches_one_shot_run(monkeypatch):
    one_shot = make_replay(three_anchor_bundle()).run()
    prefix, checkpoint = make_replay(three_anchor_bundle()).run_until(2)
    resumed = ClosedBarCausalReplay.restore(checkpoint, bundle=three_anchor_bundle()).run()
    assert resumed.digest == one_shot.digest
```

Also test closed lifecycle on a seeded PENDING and seeded OPEN row, exact
message order, unavailable/missing reversal input, unsupported source variant,
disabled/future/mismatched activation evidence, no candidate, producer block,
watch save ordering, malformed checkpoint and an attempted monkeypatch of
`TrackerAdmission.record` that fails if invoked.
Add adversarial coverage for a bound admission publication whose event is
missing, duplicated, mismatched, or future; for a changed same-ID/same-time
event payload; and for a one-shot versus checkpoint/resume replay after both
publication and reversal-input bindings are present.

- [ ] **Step 2: Run replay tests and confirm they fail**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider`

Expected: import failure because `ClosedBarCausalReplay` does not exist.

- [ ] **Step 3: Implement the minimal source-projected runner**

```python
def _run_anchor(self, anchor):
    inputs = self._inputs(anchor)
    commitments = self._validate_bound_evidence(anchor, inputs)
    if commitments is None:
        return self._blocked(anchor, stage="evidence", blocker="EVENT_BINDING_MISSING_OR_MISMATCH")
    self.admission.advance_to(anchor.decision_time)
    watch_state = self.watch.load()
    self.watch.save_before_producers(watch_state)
    messages = tuple(TrackerLifecycleCaller(self.admission).check(
        lambda state: LifecycleClosedResolver(self.admission).resolve(
            state, now=self.admission.now_epoch())))
    evaluation = _evaluate_reversal_asof(**inputs)
    candidate = _selected_candidate(evaluation.report)
    self.watch.save_final(watch_state)
    return self._append_observation(anchor, evaluation.report, candidate, messages)
```

Before each anchor, require every `required_event_id` to have
`available_at <= decision_time` and an exact matching `INTERNAL_REVERSAL_INPUT`
binding for the pass input.  Before calling `advance_to`, require every
`CausalAdmissionContext.replay_publications_through(anchor.decision_time)` item
to have one unique eligible `ADMISSION_PUBLICATION` event binding with matching
publication ID, digest, availability and channel/kind identity.  Bind and
append canonical commitments for all eligible event payloads in bundle order,
plus the Task 3 baseline fingerprint, in every record.  A changed payload must
therefore change the record digest even if its ID/time are unchanged.  Advance
only the shared clock/context after this proof; never call a wall clock. Preserve
`LifecycleClosedResolver` skip behavior per tracker record. Convert a selected
reversal report to a detached candidate observation, retaining its source plan
only in the raw ledger. Emit `UNSUPPORTED` for an unknown pass/source variant,
`BLOCKED` for missing/invalid evidence or producer errors, and `NO_CANDIDATE`
for the producer's actual no-selection result. Do not call record, gate,
delivery, output queue, broker or an economic function for a new candidate.

- [ ] **Step 4: Run the replay and dependency suites**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider`

Expected: PASS; selected candidates are observable, seeded tracker rows advance
causally, and no P&L/dataset/training field is introduced.


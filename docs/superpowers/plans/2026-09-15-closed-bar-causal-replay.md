# Closed-Bar Causal Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, resumable, closed-bar replay spine that records source-faithful internal-reversal observations and existing tracker lifecycle transitions without generating economic labels or new tracker trades.

**Architecture:** The replay contracts own immutable evidence ordering, activation evidence, raw ledger records and checkpoints. A read-only source auditor pins `scripts/market_watch.py::main` and proves the selected order. The runtime shares one replay clock across causal watch/tracker providers, resolves supplied tracker records through the accepted closed lifecycle, evaluates the accepted internal-reversal producer as an `OBSERVE_ONLY` candidate, and appends detached diagnostics to its ledger.

**Tech Stack:** Python 3.13, dataclasses, hashlib/json, pandas, pytest, AST, JSON CLI.

**Spec:** `docs/superpowers/specs/2026-09-15-closed-bar-causal-replay-design.md`

## Global Constraints

- Read and parse retained source only; never import or execute it.
- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and `scripts/market_watch.py` blob `f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`.
- Use only explicit closed/available evidence; no inferred availability, revisions, symbol aliases, calendars, thresholds or feed fallbacks.
- The first slice records new selected plans only as `OBSERVE_ONLY`; it must never call `tracker.record()` for them, regardless of activation evidence.
- Resolve lifecycle only for supplied tracker state through `TrackerLifecycleCaller` and `LifecycleClosedResolver`; preserve their source-owned gate/save and record-local order.
- No network, filesystem discovery, raw-market archive, broker, delivery, P&L, cost, fill, dataset, training, model, shadow or live behavior.
- Keep `ready_for_replay` and `ready_for_training` false in every public report.
- Do not commit or push from this dirty shared worktree without explicit authorization. Record acceptance in `agent-exchange/status/` instead.

---

### Task 1: Immutable replay evidence, ledger and activation contracts

**Files:**
- Create: `trading_system/tree_replay/causal_replay_contracts.py`
- Create: `tests/tree_replay/test_causal_replay_contracts.py`

**Interfaces:**
- Produces frozen `TrackerActivationEvidence`, `ReplayEvent`, `ReplayPassAnchor`, `ReplayEvidenceBundle`, `ReplayPassRecord`, and `ReplayRunLedger`.
- `canonical_digest(value: object) -> str` accepts only recursively finite JSON-compatible values and returns a SHA-256 digest of canonical UTF-8 JSON.
- `ReplayEvidenceBundle.events_before_or_at(at: datetime) -> tuple[ReplayEvent, ...]` returns only events whose `available_at <= at`; validation happens before selection.
- `ReplayRunLedger.append(record: ReplayPassRecord) -> ReplayRunLedger` returns a new ledger and rejects noncontiguous pass indexes, duplicate IDs, backward decision times and invalid predecessor digest.

- [x] **Step 1: Write the failing contract tests**

```python
def test_anchor_requires_strict_schedule_and_exact_activation_coverage():
    activation = TrackerActivationEvidence(
        evidence_id="activation-1", source="watch-config", variant="level_reversal:5m",
        observed_at=T0, available_at=T0, covered_through=T1, enabled=True,
    )
    anchor = ReplayPassAnchor(
        pass_id="pass-1", decision_time=T1, source_variant="level_reversal:5m",
        required_event_ids=("bars-1",), activation=activation,
    )
    assert anchor.activation_state() == "EVIDENCED_ENABLED"

    with pytest.raises(ValueError, match="strictly increasing"):
        ReplayEvidenceBundle(run_id="run-1", instrument="OANDA:XAUUSD",
                             events=(event(T1, 1), event(T1, 0)), anchors=(anchor,))

def test_ledger_is_append_only_and_hash_chained():
    ledger = ReplayRunLedger.empty("run-1")
    first = ledger.append(record(index=0, predecessor_digest=ledger.digest))
    assert first.records[0].outcome == "OBSERVE_ONLY"
    with pytest.raises(ValueError, match="predecessor"):
        first.append(record(index=1, predecessor_digest="wrong"))
```

Include cases for naive/sub-microsecond times, duplicate event/pass IDs, a
future/uncovered/mismatched-variant activation record, nonfinite numbers,
unknown event kinds, event payload-availability mismatch, and a candidate
record that tries to contain `net_pnl`, `net_R`, `success` or `failure`.

- [x] **Step 2: Run the contract tests and confirm they fail**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider`

Expected: import failure because `causal_replay_contracts` does not exist.

- [x] **Step 3: Implement exact frozen contracts and canonical serialization**

```python
@dataclass(frozen=True, kw_only=True)
class TrackerActivationEvidence:
    evidence_id: str
    source: str
    variant: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    enabled: bool

    def state_at(self, *, decision_time: datetime, variant: str) -> str:
        at = _utc(decision_time, "decision_time")
        if variant != self.variant:
            return "MISMATCHED_VARIANT"
        if at < self.available_at:
            return "NOT_YET_AVAILABLE"
        if at > self.covered_through:
            return "COVERAGE_EXPIRED"
        return "EVIDENCED_ENABLED" if self.enabled else "EVIDENCED_DISABLED"

@dataclass(frozen=True, kw_only=True)
class ReplayPassRecord:
    pass_index: int
    pass_id: str
    decision_time: datetime
    outcome: str
    consumed_event_ids: tuple[str, ...]
    activation_state: str
    candidate: dict | None
    lifecycle_messages: tuple[tuple[str, bool], ...]
    diagnostics: tuple[dict, ...]
    predecessor_digest: str
```

Use the existing `bars._utc`, `_number`, `_validate_identity` and `state._identity`
helpers rather than accepting alternate time/instrument formats. Make all
exported collections tuples or detached canonical dictionaries. Permit exactly
`OBSERVE_ONLY`, `NO_CANDIDATE`, `BLOCKED`, `SKIPPED`, and `UNSUPPORTED` as
record outcomes. Validate candidate and diagnostics recursively before hashing.

- [x] **Step 4: Run the focused contract suite**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider`

Expected: PASS; no contract creates a tracker row or economic field.

### Task 2: Source-pinned outer-pass intake and fail-closed audit

**Files:**
- Create: `trading_system/tree_spec/causal_replay_source.py`
- Create: `tools/check_causal_replay_source_parity.py`
- Create: `tests/tree_spec/test_causal_replay_source.py`
- Create: `configs/trees/causal-replay-source-contracts.json`
- Create: `docs/architecture/CAUSAL-REPLAY-SOURCE-INTAKE.md`

**Interfaces:**
- `check_source_parity(source_root: Path) -> dict` parses `scripts/market_watch.py`; it never imports it.
- Returns schema-valid `VERIFIED` only after validating commit/blob pins and the required source order; every failure returns `BLOCKED`, a nonempty string blocker list, `ready_for_replay=False`, and `ready_for_training=False`.
- The CLI requires `--source-root`, prints only JSON, and exits `0` for `VERIFIED`, `2` for `BLOCKED`.

- [x] **Step 1: Write mutation-based source-audit tests**

```python
def test_audit_requires_lifecycle_before_level_reversal(tmp_path):
    root = copied_retained_source(tmp_path)
    mutate(root / "scripts" / "market_watch.py",
           "_msgs = tracker.closeout_check() + tracker.check()",
           "_msgs = tracker.closeout_check() + tracker.check()\n# moved")
    report = check_source_parity(root)
    assert report["status"] == "BLOCKED"
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]

def test_audit_retains_record_only_inside_alert_enabled_branch():
    report = check_source_parity(RETAINED_ROOT)
    assert report["projection"]["level_reversal_record_guard"] == "--telegram"
    assert report["ready_for_training"] is False
```

Mutate source blob/commit, state load, pre-producer state write, tracker lock
and `closeout_check()+check()` order, lifecycle gate, `level_reversal.find`,
reversal-before-tree/engine placement, `tracker.record`, alert guard and final
state write. Also mutate the runtime manifest, malformed child report and CLI
root exception path.

- [x] **Step 2: Run the audit tests and confirm they fail**

Run: `python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider`

Expected: import failure because the audit module and CLI do not exist.

- [x] **Step 3: Implement AST projection and manifest validation**

```python
REQUIRED_ORDER = (
    "watch_state_load", "watch_state_preproducer_save", "tracker_closed_pass",
    "tracker_gate", "level_reversal_find", "level_reversal_outer_gates",
    "level_reversal_record_alert_guard", "watch_state_final_save",
)

def check_source_parity(source_root: Path) -> dict:
    report = _empty_report()
    try:
        source = _read_pinned_market_watch(source_root)
        main = _unique_main(ast.parse(source.text))
        projection = _project_required_order(main)
    except Exception as exc:
        return _blocked(report, f"SOURCE_READ_OR_PARSE:{type(exc).__name__}")
    blockers = _validate_projection(projection)
    if blockers:
        return _blocked(report, *blockers)
    return _verified(report, projection)
```

The implementation must prove the actual retained ordering from `main()`:
state load at lines 494-495; pre-producer state write before tracker lifecycle;
the locked `closeout_check() + check()` pass and gate at lines 962-972;
`level_reversal.find` before tree/engine; all outer gates before
`tracker.record`; the `--telegram` guard enclosing record; and final state
write at line 1599. The projection must label windows, market-closed,
producer-arbitration, post-stop, occupied-slot and same-level gates as
`UNWIRED_OUTER_ADMISSION`, never replace them with booleans.

- [x] **Step 4: Run source proof and command**

Run: `python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: PASS and `VERIFIED`; both readiness flags remain false.

### Task 3: Shared clock and resumable causal-provider snapshot

**Files:**
- Modify: `trading_system/tree_replay/admission_context.py`
- Modify: `trading_system/tree_replay/admission_io.py`
- Modify: `trading_system/tree_replay/watch_storage.py`
- Create: `trading_system/tree_replay/causal_replay_checkpoint.py`
- Create: `tests/tree_replay/test_causal_replay_checkpoint.py`
- Modify: `tests/tree_replay/test_admission_context.py`
- Modify: `tests/tree_replay/test_shared_clock.py`

**Interfaces:**
- `CausalAdmissionContext(..., clock: ReplayClock | None = None)` accepts only an exact clock at the declared initial decision time; omitted clock preserves existing behavior.
- `CausalAdmissionContext.replay_snapshot() -> dict` returns detached canonical seeds, current frame requests, remaining publications, remaining lock steps and clock time.
- `CausalAdmissionContext.from_replay_snapshot(snapshot: dict, *, clock: ReplayClock) -> CausalAdmissionContext` reconstructs only a canonical, matching snapshot.
- `checkpoint_from(*, bundle, ledger, next_pass_index, watch, admission) -> dict` and `restore_checkpoint(checkpoint, *, bundle, clock) -> RestoredReplayState` require matching source/event/bundle fingerprints.

- [x] **Step 1: Write failing shared-clock and resume tests**

```python
def test_context_and_watch_share_one_monotonic_clock():
    clock = ReplayClock(T0)
    context = make_context(decision_time=T0, clock=clock)
    watch = CausalWatchStorage(seed=watch_seed(T0), decision_time=T0, clock=clock)
    context.advance_to(T1)
    assert watch.snapshot().observed_at == T1
    assert context.decision_time == T1

def test_snapshot_resume_rejects_changed_event_order_and_preserves_state():
    state = checkpoint_from(bundle=BUNDLE, ledger=ledger(), next_pass_index=1,
                            watch=watch_at_t1(), admission=context_at_t1())
    restored = restore_checkpoint(state, bundle=BUNDLE, clock=ReplayClock(T1))
    assert restored.next_pass_index == 1
    with pytest.raises(ValueError, match="bundle fingerprint"):
        restore_checkpoint(state, bundle=changed_order_bundle(), clock=ReplayClock(T1))
```

Cover future/reversed clock calls, malformed snapshot checksum, altered source
pin, altered ledger digest, consumed publication resurrection, consumed lock
step resurrection, and mutations of returned snapshots.

- [x] **Step 2: Run focused tests and confirm they fail**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider`

Expected: failure because the optional shared clock and replay checkpoint API do not exist.

- [x] **Step 3: Add backward-compatible shared clock and canonical snapshots**

```python
def __init__(self, *, instrument, decision_time, tracker_seed, quote_seed,
             log_seed, busy_seed, newline, frame_requests, publications,
             lock_steps, clock=None):
    at = _utc(decision_time, "decision_time")
    if clock is None:
        clock = ReplayClock(at)
    _validate_binding(clock, at)
    self._clock = clock

def replay_snapshot(self):
    return _canonical_snapshot(
        decision_time=self.decision_time,
        tracker=self._storage.snapshot(), quotes=self._quotes.snapshot(),
        watch_log=self._log.snapshot(), busy=_busy_seed(self._busy),
        frame_requests=self._frame_requests,
        publications=self._publications[self._publication_index:],
        lock_steps=self._steps[self._step_index:],
    )
```

Add a detached `CausalQuoteReader.snapshot()` mirroring the existing log
snapshot. Preserve all existing constructor behavior and tests when `clock` is
omitted. Snapshot restoration must use constructors and public validation, not
assign private mutable provider fields. The checkpoint hash must cover the
bundle fingerprint, ledger digest, next pass index, shared-clock time, watch
snapshot and admission snapshot.

- [x] **Step 4: Run compatibility and checkpoint suites**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider`

Expected: PASS; existing causal providers retain their prior behavior.

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

- [x] **Step 1: Write failing replay behavior tests**

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

- [x] **Step 2: Run replay tests and confirm they fail**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider`

Expected: import failure because `ClosedBarCausalReplay` does not exist.

- [x] **Step 3: Implement the minimal source-projected runner**

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

- [x] **Step 4: Run the replay and dependency suites**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider`

Expected: PASS; selected candidates are observable, seeded tracker rows advance
causally, and no P&L/dataset/training field is introduced.

### Task 5: Usage documentation, full acceptance and independent review

**Files:**
- Create: `docs/architecture/CAUSAL-REPLAY-USAGE.md`
- Modify: `AGENTS.md`
- Modify: `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- Modify: `docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`
- Create: `agent-exchange/status/<UTC>-codex-closed-bar-causal-replay.md`

**Interfaces:**
- Usage documentation exposes only supplied-evidence construction, run/resume,
  ledger inspection, source-audit command and the complete excluded-scope list.
- Acceptance status reports exact test/CLI evidence and says training readiness
  is false.

- [x] **Step 1: Write the user-facing usage contract before acceptance**

```python
ledger = ClosedBarCausalReplay(
    bundle, clock=ReplayClock(bundle.start_at), watch=watch,
    admission=admission, reversal_inputs=inputs,
).run()
assert all(row.outcome != "SUCCESS" for row in ledger.records)
assert all("net_pnl" not in row.as_dict() for row in ledger.records)
```

Document that the run uses synthetic/supplied evidence only; historical vendor
data, raw-data retention, outer admission, new tracker registration, economics,
dataset construction and model fitting remain separate work and permissions.

- [x] **Step 2: Run all acceptance evidence**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_causal_replay_source.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: every test passes; CLI reports `VERIFIED`; both readiness flags are false.

- [x] **Step 3: Obtain independent final review**

The reviewer must inspect the source-order audit, contracts, checkpoint restore,
runner order and test mutations. The review must reject any new tracker record,
delivery, economic label, raw-data write, source execution or readiness claim.

- [x] **Step 4: Record bounded acceptance**

Mark completed checkboxes only after the evidence and final review pass. Update
the tracker to state precisely: closed-bar causal replay now records raw
internal-reversal observations and supplied tracker lifecycle, while full outer
admission, remaining producers, economics, dataset, training, evaluation and
all production permissions remain open.

## Self-Review

- Spec coverage: Tasks 1 and 3 implement evidence/ledger/checkpoint contracts; Task 2 pins source order; Task 4 connects the accepted components without creating new trades; Task 5 documents and independently accepts every boundary.
- Placeholder scan: every task declares files, exported interfaces, failing tests, commands and expected results; no task infers trading, cost, data or source policy.
- Type consistency: Task 1 bundle/anchor/ledger types feed Task 3 checkpoints and Task 4 runner; Task 3 shared `ReplayClock` is consumed by the Task 4 watch/admission pair; Task 2 remains static and is never imported by the runtime.

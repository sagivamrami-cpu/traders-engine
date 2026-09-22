# Independent review — Task 3 shared clock and causal-provider checkpoint

Reviewer: Codex

Target: Task 3 of `docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`, using `docs/superpowers/specs/2026-09-15-closed-bar-causal-replay-design.md` and `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-3-report.md`. No standalone Task 3 brief exists in the task directory.

Created at: 2026-09-14

Status: CHANGES_REQUESTED

Verdict: The new snapshots are detached and checksummed, restore does route objects through public constructors, and the focused 27-test checkpoint/shared-clock suite passes. However, the checkpoint accepts checksum-recomputed state that is causally incompatible with the bundle or original providers. This violates the Task 3 resume and exact shared-clock contract, so it is not ready for Task 4 to rely on.

## Findings

### Critical — completed ledger rows are not bound to the immutable bundle schedule

Evidence:

- `restore_checkpoint()` rebuilds a self-consistent `ReplayRunLedger` at [causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/causal_replay_checkpoint.py:81) and then only checks `next_pass_index == len(ledger.records)` at line 85. It never compares a restored record's `pass_id` or `decision_time` to `bundle.anchors[:next_pass_index]`, nor validates completed record/event correspondence against the bundle.
- `checkpoint_from()` has the same gap at lines 45-64: a legal ledger with the correct run ID and length can be serialized for any prefix index.
- The supplied Task 3 fixture demonstrates the defect without tampering: its `ledger()` creates the sole record at `T` ([test_causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/tests/tree_replay/test_causal_replay_checkpoint.py:44)), while the bundle's sole anchor is at `T + 1 second` (line 39). `checkpoint_from()` and `restore_checkpoint()` accept it.

Independent in-memory probe output after a normal create/restore was `ledger_anchor_time_match= False`. The resumed runner would start at index 1 and treat an anchor as completed even though the ledger record is for a different decision time. A checksum is not a remedy: an attacker can recompute it over a locally valid but bundle-incompatible ledger.

Required correction: reject creation and restore unless every completed record precisely corresponds to the same indexed bundle anchor (at minimum pass ID and decision time, plus the intended consumed-event invariants). Add a recomputed-checksum adversarial test, not only a digest-mutation test.

### Critical — no independent source/provider baseline fingerprint prevents forged source, future publication, or future lock evidence

Evidence:

- The outer checkpoint state has only `bundle_fingerprint`, ledger information, clock time, watch seed, and admission snapshot ([causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/causal_replay_checkpoint.py:59)). There is no immutable fingerprint for the initial watch/admission provider evidence or the original remaining publication/lock schedules.
- On restore, `_watch_seed()` only reconstructs a structurally valid `WatchStateSeed` (lines 108-115). `CausalAdmissionContext.from_replay_snapshot()` checks merely that remaining publications are after the current time and remaining locks have not started ([admission_context.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/admission_context.py:369)); it has no expected original schedule to compare.
- Therefore a checksum-recomputed checkpoint can replace a watch/source identity or replace/add a well-formed future publication/lock sequence. Constructor validation proves only that the forged evidence is well-formed, not that it is the evidence the run began with.

Independent in-memory probe changed only `state.watch.source` to `forged-source`, recomputed the outer canonical checksum, and restored successfully: `forged_watch_source_restored= forged-source`. The existing test called “changed source” changes the bundle event source ([test_causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/tests/tree_replay/test_causal_replay_checkpoint.py:73)); it does not exercise provider-source or future-schedule substitution.

This conflicts with the plan's required matching source/event/bundle fingerprints and the design requirement that resume reject mismatched initial artifact identity and source-pin fingerprints. Required correction: bind immutable provider/source/schedule fingerprints into a trusted replay input (normally the bundle or an explicit expected-provider descriptor passed to restore), and reject any mismatch after reconstructing the checkpoint image. A self-contained checksum cannot authenticate a checksum-recomputed checkpoint.

### Important — checkpoint creation does not prove that watch and admission share the same ReplayClock instance

Evidence:

- Individual providers validate only exact clock type and equal initial time. `checkpoint_from()` checks only `watch_seed.observed_at != admission.decision_time` ([causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/causal_replay_checkpoint.py:54)), not object identity of `watch.source._clock` and `admission._clock`.
- The restore path correctly gives both rebuilt providers the supplied single clock (lines 97-98), but that retroactively merges independent histories instead of rejecting an illegally assembled input checkpoint.

Independent in-memory probe constructed admission and watch with two distinct `ReplayClock` instances, advanced both to the same time, and `checkpoint_from()` accepted them: `distinct_shared_clock_instances_accepted= True`. The required one-clock replay boundary is therefore not enforced at checkpoint creation. Require the identical clock object (and add a negative test); preserve omitted-clock constructor behavior outside explicit replay assembly.

### Important — serialized timestamps with more than six fractional digits are silently truncated on both surfaces

Evidence:

- Snapshot restore parses every serialized timestamp through `_parse_time()` ([admission_context.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/admission_context.py:451)); checkpoint restore uses the analogous `_time()` ([causal_replay_checkpoint.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/causal_replay_checkpoint.py:136)). Both call `datetime.fromisoformat()` with no pre-parse fractional-second precision check.
- CPython accepts `2026-09-14T12:34:56.1234567+00:00` and returns `2026-09-14T12:34:56.123456+00:00`; it does not reject the seventh digit.
- A recomputed checkpoint with only `watch.covered_through` changed to a seven-digit timestamp restored and emitted the truncated six-digit time: `checkpoint_submicro_watch_accepted= 2026-09-09T16:01:00+00:00`. A similarly recomputed admission snapshot with only the quote seed's packed `covered_through` changed restored and emitted `snapshot_submicro_quote_accepted= 2026-09-09T16:05:00+00:00`.

The result is a non-canonical serialized value silently becoming a different internal instant, defeating the explicit microsecond-exact replay boundary. Reject any ISO timestamp carrying a fractional component longer than six digits before `fromisoformat()` on both restore surfaces, including packed dataclass timestamps, and test both standalone snapshot and outer checkpoint with recomputed checksums.

## Confirmed positive scope

- `replay_snapshot()` and `checkpoint_from()` return deep-copied JSON-shaped images; reconstruction goes through `CausalWatchStorage` and `CausalAdmissionContext.from_replay_snapshot()`, rather than assigning private provider state.
- Existing consumed-publication and past-lock resurrection guards are present at [admission_context.py](C:/Users/roeea/sagiv-repos/traders-engine/trading_system/tree_replay/admission_context.py:369), but are insufficient against structurally valid substituted future evidence without a baseline fingerprint.
- No Task 3 runtime path adds tracker recording, delivery, economic fields, dataset/training/model behavior, retained-source execution, or a readiness-positive report. The only public readiness fields found remain false in `CausalAdmissionContext.report()`.

## Verification reviewed

- `python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider` — PASS: `27 passed in 1.84s`.
- Focused read-only adversarial in-memory probes — reproduced all four findings above; no retained external source was imported or executed.

## Recommended next action

Revise Task 3 before acceptance. Add trusted immutable provider/source/schedule fingerprints, enforce the single shared `ReplayClock` object at checkpoint creation, bind the ledger prefix exactly to bundle anchors, and reject submicrosecond serialized times at every snapshot/checkpoint parser. Then rerun the five-suite compatibility command recorded in the Task 3 report plus the new recomputed-checksum probes.

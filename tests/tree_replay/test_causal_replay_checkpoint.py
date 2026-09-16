"""Task 3 replay checkpoint boundaries; no runner, source access, or trade effects."""
from copy import deepcopy
from datetime import timedelta

import pytest

from trading_system.tree_replay.causal_replay_checkpoint import (
    ReplayProviderBaseline, checkpoint_from, restore_checkpoint,
)
from trading_system.tree_replay.causal_replay_contracts import (
    ReplayEvent, ReplayEvidenceBundle, ReplayPassAnchor, ReplayPassRecord,
    ReplayRunLedger, TrackerActivationEvidence,
)
from trading_system.tree_replay.clock import ReplayClock
from trading_system.tree_replay.watch_storage import CausalWatchStorage, WatchStateSeed
from test_admission_context import T, SYMBOL, context, publication, seed, step, steps


def bundle(*, reordered=False, source="synthetic"):
    events = (
        ReplayEvent(event_id="event-a", available_at=T, sequence=0,
                    kind="WATCH_PUBLICATION", source=source, variant="level-reversal:5m",
                    payload={"available_at": T.isoformat()}),
        ReplayEvent(event_id="event-b", available_at=T + timedelta(seconds=1), sequence=0,
                    kind="WATCH_PUBLICATION", source=source, variant="level-reversal:5m",
                    payload={"available_at": (T + timedelta(seconds=1)).isoformat()}),
    )
    if reordered:
        events = (
            ReplayEvent(event_id="event-b", available_at=T, sequence=0,
                        kind="WATCH_PUBLICATION", source=source, variant="level-reversal:5m",
                        payload={"available_at": T.isoformat()}),
            ReplayEvent(event_id="event-a", available_at=T + timedelta(seconds=1), sequence=0,
                        kind="WATCH_PUBLICATION", source=source, variant="level-reversal:5m",
                        payload={"available_at": (T + timedelta(seconds=1)).isoformat()}),
        )
    activation = TrackerActivationEvidence(evidence_id="activation", source="synthetic",
        variant="level-reversal:5m", observed_at=T, available_at=T,
        covered_through=T + timedelta(minutes=1), enabled=True)
    return ReplayEvidenceBundle(run_id="run", instrument=SYMBOL, events=events,
        anchors=(ReplayPassAnchor(pass_id="pass", decision_time=T + timedelta(seconds=1),
                                  source_variant="level-reversal:5m",
                                  required_event_ids=("event-a",), activation=activation),))


def ledger():
    first = ReplayRunLedger.empty("run")
    return first.append(ReplayPassRecord(pass_index=0, pass_id="pass", decision_time=T + timedelta(seconds=1),
        outcome="NO_CANDIDATE", consumed_event_ids=("event-a", "event-b"), activation_state="EVIDENCED_ENABLED",
        candidate=None, lifecycle_messages=(), diagnostics=(), predecessor_digest=first.digest))


def watch(clock):
    return CausalWatchStorage(seed=WatchStateSeed(seed_id="watch", source="synthetic",
        observed_at=T, available_at=T, covered_through=T + timedelta(minutes=1),
        status="PRESENT", text="{}"), decision_time=T, clock=clock)


def checkpoint():
    clock = ReplayClock(T)
    admission = context(clock=clock, lock_steps=())
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission.advance_to(T + timedelta(seconds=1))
    return checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                           watch=state_watch, admission=admission, baseline=baseline), baseline


def test_checkpoint_resume_detaches_and_rejects_changed_bundle_order_or_source():
    state, baseline = checkpoint()
    restored = restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)
    assert restored.next_pass_index == 1
    state["state"]["watch"]["text"] = '{"forged":true}'
    assert restored.watch.load() == {}
    with pytest.raises(ValueError, match="bundle fingerprint"):
        altered, baseline = checkpoint()
        restore_checkpoint(altered, bundle=bundle(source="other"), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)
    with pytest.raises(ValueError, match="bundle fingerprint"):
        altered, baseline = checkpoint()
        restore_checkpoint(altered, bundle=bundle(reordered=True), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


@pytest.mark.parametrize("path", [
    ("checksum",), ("state", "ledger_digest"), ("state", "admission", "checksum"),
    ("state", "admission", "state", "publications"), ("state", "admission", "state", "lock_steps"),
])
def test_checkpoint_rejects_tampered_digest_or_resurrected_remaining_evidence(path):
    state, baseline = checkpoint()
    target = state
    for key in path[:-1]:
        target = target[key]
    key = path[-1]
    target[key] = "0" * 64 if key in ("checksum", "ledger_digest") else ([{}] if key == "publications" else [{}])
    with pytest.raises(ValueError):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def test_checkpoint_creation_rejects_a_legal_ledger_for_the_wrong_bundle_anchor():
    clock = ReplayClock(T)
    admission = context(clock=clock, lock_steps=())
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission.advance_to(T + timedelta(seconds=1))
    first = ReplayRunLedger.empty("run")
    wrong = first.append(ReplayPassRecord(
        pass_index=0, pass_id="pass", decision_time=T, outcome="NO_CANDIDATE",
        consumed_event_ids=(), activation_state="EVIDENCED_ENABLED", candidate=None,
        lifecycle_messages=(), diagnostics=(), predecessor_digest=first.digest,
    ))
    with pytest.raises(ValueError, match="ledger record 0"):
        checkpoint_from(bundle=bundle(), ledger=wrong, next_pass_index=1,
                        watch=state_watch, admission=admission, baseline=baseline)


def test_restore_rejects_checksum_recomputed_bundle_incompatible_ledger():
    state, baseline = checkpoint()
    first = ReplayRunLedger.empty("run")
    wrong = first.append(ReplayPassRecord(
        pass_index=0, pass_id="pass", decision_time=T, outcome="NO_CANDIDATE",
        consumed_event_ids=(), activation_state="EVIDENCED_ENABLED", candidate=None,
        lifecycle_messages=(), diagnostics=(), predecessor_digest=first.digest,
    ))
    state["state"]["ledger"] = wrong.as_dict()
    state["state"]["ledger_digest"] = wrong.digest
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="ledger record 0"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def test_restore_rejects_checksum_recomputed_provider_source_or_future_schedule_substitution():
    state, baseline = checkpoint_with_future_provider_evidence()
    state["state"]["watch"]["source"] = "forged-source"
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)

    state, baseline = checkpoint_with_future_provider_evidence()
    state["state"]["admission"]["state"]["publications"]["items"][0]["fields"]["source"] = "forged-publication"
    _rehash_admission_snapshot(state)
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)

    state, baseline = checkpoint_with_future_provider_evidence()
    state["state"]["admission"]["state"]["lock_steps"]["items"][0]["fields"]["step_id"] = "forged-lock"
    _rehash_admission_snapshot(state)
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def test_restore_rejects_checksum_recomputed_future_publication_addition():
    from trading_system.tree_replay.admission_context import Publication, _pack

    state, baseline = checkpoint_with_future_provider_evidence()
    later = T + timedelta(seconds=3)
    added = Publication(
        publication_id="added-publication", source="synthetic", channel="tracker",
        payload=seed("tracker", at=later, value='{"added":{}}'), available_at=later, sequence=0,
    )
    state["state"]["admission"]["state"]["publications"]["items"].append(_pack(added))
    _rehash_admission_snapshot(state)
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def test_checkpoint_creation_rejects_clock_before_last_consumed_anchor_without_provider_schedules():
    clock = ReplayClock(T)
    admission = context(clock=clock, lock_steps=())
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)

    with pytest.raises(ValueError, match="last consumed anchor"):
        checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                        watch=state_watch, admission=admission, baseline=baseline)


def test_restore_rejects_checksum_recomputed_clock_before_last_consumed_anchor_without_provider_schedules():
    state, baseline = checkpoint()
    _backdate_checkpoint(state, T)

    with pytest.raises(ValueError, match="last consumed anchor"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T), baseline=baseline)


def test_restore_rejects_checksum_recomputed_backdate_before_consumed_publication():
    state, baseline = checkpoint_with_consumed_publication()
    restored = restore_checkpoint(
        state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=2)), baseline=baseline,
    )
    assert restored.next_pass_index == 1

    _backdate_checkpoint(state, T + timedelta(seconds=1))
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(
            state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline,
        )


def test_restore_rejects_checksum_recomputed_backdate_before_consumed_lock_step():
    state, baseline = checkpoint_with_consumed_lock_step()
    restored = restore_checkpoint(
        state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=2)), baseline=baseline,
    )
    assert restored.next_pass_index == 1

    _backdate_checkpoint(state, T + timedelta(seconds=1))
    with pytest.raises(ValueError, match="provider baseline"):
        restore_checkpoint(
            state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline,
        )


def test_checkpoint_creation_requires_the_same_clock_object_for_both_providers():
    admission_clock = ReplayClock(T)
    watch_clock = ReplayClock(T)
    admission = context(clock=admission_clock, lock_steps=())
    state_watch = watch(watch_clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission_clock.advance_to(T + timedelta(seconds=1))
    watch_clock.advance_to(T + timedelta(seconds=1))
    with pytest.raises(ValueError, match="same ReplayClock object"):
        checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                        watch=state_watch, admission=admission, baseline=baseline)


def test_restore_rejects_checksum_recomputed_submicrosecond_checkpoint_timestamp():
    state, baseline = checkpoint()
    state["state"]["watch"]["covered_through"] = "2026-09-09T16:01:00.1234567+00:00"
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="microsecond-exact"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def test_restore_rejects_checksum_recomputed_basic_submicrosecond_checkpoint_timestamp():
    state, baseline = checkpoint()
    state["state"]["watch"]["covered_through"] = "20260909T160100.0000000+0000"
    _rehash_checkpoint(state)
    with pytest.raises(ValueError, match="microsecond-exact"):
        restore_checkpoint(state, bundle=bundle(), clock=ReplayClock(T + timedelta(seconds=1)), baseline=baseline)


def checkpoint_with_future_provider_evidence():
    clock = ReplayClock(T)
    future = T + timedelta(seconds=2)
    admission = context(
        clock=clock,
        publications=(publication("tracker", seed("tracker", at=future, value='{"future":{}}'), at=future),),
        lock_steps=(step("prepare", future, index=0),),
    )
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission.advance_to(T + timedelta(seconds=1))
    return checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                           watch=state_watch, admission=admission, baseline=baseline), baseline


def checkpoint_with_consumed_publication():
    clock = ReplayClock(T)
    future = T + timedelta(seconds=2)
    admission = context(
        clock=clock,
        publications=(publication("tracker", seed("tracker", at=future, value='{"future":{}}'), at=future),),
        lock_steps=(),
    )
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission.advance_to(future)
    return checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                           watch=state_watch, admission=admission, baseline=baseline), baseline


def checkpoint_with_consumed_lock_step():
    clock = ReplayClock(T)
    future = T + timedelta(seconds=2)
    admission = context(clock=clock, publications=(), lock_steps=steps(start=future, seconds=0))
    state_watch = watch(clock)
    baseline = ReplayProviderBaseline.capture(watch=state_watch, admission=admission)
    admission.advance_to(future)
    with admission.locked():
        pass
    return checkpoint_from(bundle=bundle(), ledger=ledger(), next_pass_index=1,
                           watch=state_watch, admission=admission, baseline=baseline), baseline


def _backdate_checkpoint(checkpoint, at):
    checkpoint["state"]["clock_time"] = at.isoformat()
    checkpoint["state"]["admission"]["state"]["decision_time"] = at.isoformat()
    checkpoint["state"]["watch"]["observed_at"] = at.isoformat()
    checkpoint["state"]["watch"]["available_at"] = at.isoformat()
    _rehash_admission_snapshot(checkpoint)
    _rehash_checkpoint(checkpoint)


def _rehash_admission_snapshot(checkpoint):
    from trading_system.tree_replay.causal_replay_contracts import canonical_digest
    snapshot = checkpoint["state"]["admission"]
    snapshot["checksum"] = canonical_digest(snapshot["state"])


def _rehash_checkpoint(checkpoint):
    from trading_system.tree_replay.causal_replay_contracts import canonical_digest
    checkpoint["checksum"] = canonical_digest(checkpoint["state"])

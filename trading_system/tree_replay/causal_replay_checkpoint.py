"""Validated, detached checkpoints for the closed-bar replay spine only."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import re

from .admission_context import CausalAdmissionContext, _unpack
from .causal_replay_contracts import (
    ReplayEvidenceBundle, ReplayPassRecord, ReplayRunLedger, canonical_digest,
)
from .clock import ReplayClock, _validate_binding
from .watch_storage import CausalWatchStorage, WatchStateSeed
from .bars import _utc


_SCHEMA = "closed-bar-causal-replay-checkpoint-v1"


@dataclass(frozen=True, kw_only=True)
class RestoredReplayState:
    ledger: ReplayRunLedger
    next_pass_index: int
    watch: CausalWatchStorage
    admission: CausalAdmissionContext


@dataclass(frozen=True, init=False)
class ReplayProviderBaseline:
    """Trusted, externally retained identity and schedule baseline for checkpoint resume.

    The checkpoint carries only this object's fingerprint.  Callers must retain
    and pass the captured object separately to restore; a recomputed checkpoint
    checksum therefore cannot authorize replacement provider evidence.
    """

    _payload: dict
    _fingerprint: str

    def __init__(self, *, payload: dict):
        if type(payload) is not dict:
            raise ValueError("provider baseline payload must be canonical")
        copied = deepcopy(payload)
        object.__setattr__(self, "_payload", copied)
        object.__setattr__(self, "_fingerprint", canonical_digest(copied))

    @classmethod
    def capture(cls, *, watch, admission):
        if type(watch) is not CausalWatchStorage or type(admission) is not CausalAdmissionContext:
            raise ValueError("provider baseline requires exact causal providers")
        if type(watch.source.seed) is not WatchStateSeed:
            raise ValueError("provider baseline requires an exact watch seed")
        return cls(payload={
            "watch": _seed_identity(watch.source.seed),
            "admission": admission._replay_provider_baseline(),
        })

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def _matches_providers(self, *, watch, admission) -> bool:
        return (
            _seed_identity(watch.source.seed) == self._payload["watch"]
            and admission._replay_provider_baseline() == self._payload["admission"]
        )

    def _matches_checkpoint(self, *, watch, admission_snapshot, decision_time) -> bool:
        if type(watch) is not WatchStateSeed or type(admission_snapshot) is not dict:
            return False
        if _seed_identity(watch) != self._payload["watch"]:
            return False
        snapshot_state = admission_snapshot.get("state")
        if type(snapshot_state) is not dict:
            return False
        initial = self._payload["admission"]
        try:
            if snapshot_state["instrument"] != initial["instrument"] or snapshot_state["newline"] != initial["newline"]:
                return False
            initial_publications = _unpack(initial["publications"])
            remaining_publications = _unpack(snapshot_state["publications"])
            initial_steps = _unpack(initial["lock_steps"])
            remaining_steps = _unpack(snapshot_state["lock_steps"])
            publication_index = _suffix_index(initial_publications, remaining_publications)
            step_index = _suffix_index(initial_steps, remaining_steps)
            if any(publication.available_at > decision_time
                   for publication in initial_publications[:publication_index]):
                return False
            if any(step.started_at > decision_time or step.completed_at > decision_time
                   for step in initial_steps[:step_index]):
                return False
            expected = {
                "tracker": _unpack(initial["tracker"]), "quotes": _unpack(initial["quotes"]),
                "watch_log": _unpack(initial["watch_log"]), "busy": _unpack(initial["busy"]),
            }
            expected_frames = _unpack(initial["frame_requests"])
            for publication in initial_publications[:publication_index]:
                if publication.channel == "frames":
                    expected_frames = publication.payload
                else:
                    expected[publication.channel] = publication.payload
            if _unpack(snapshot_state["frame_requests"]) != expected_frames:
                return False
            return all(
                _seed_identity(_unpack(snapshot_state[channel])) == _seed_identity(seed)
                for channel, seed in expected.items()
            )
        except (KeyError, TypeError, ValueError):
            return False


def _bundle_fingerprint(bundle: ReplayEvidenceBundle) -> str:
    if type(bundle) is not ReplayEvidenceBundle:
        raise ValueError("bundle must be an exact ReplayEvidenceBundle")
    return canonical_digest({
        "run_id": bundle.run_id, "instrument": bundle.instrument,
        "events": [event.as_dict() for event in bundle.events],
        "anchors": [{
            "pass_id": anchor.pass_id, "decision_time": anchor.decision_time.isoformat(),
            "source_variant": anchor.source_variant, "required_event_ids": list(anchor.required_event_ids),
            "activation": {
                "evidence_id": anchor.activation.evidence_id, "source": anchor.activation.source,
                "variant": anchor.activation.variant, "observed_at": anchor.activation.observed_at.isoformat(),
                "available_at": anchor.activation.available_at.isoformat(),
                "covered_through": anchor.activation.covered_through.isoformat(), "enabled": anchor.activation.enabled,
            },
        } for anchor in bundle.anchors],
    })


def checkpoint_from(*, bundle, ledger, next_pass_index, watch, admission, baseline) -> dict:
    bundle_fingerprint = _bundle_fingerprint(bundle)
    if type(ledger) is not ReplayRunLedger or ledger.run_id != bundle.run_id:
        raise ValueError("ledger must exactly match bundle run_id")
    if type(next_pass_index) is not int or not 0 <= next_pass_index <= len(bundle.anchors):
        raise ValueError("next_pass_index must be within bundle anchors")
    if next_pass_index != len(ledger.records):
        raise ValueError("next_pass_index must equal consumed ledger records")
    if type(watch) is not CausalWatchStorage or type(admission) is not CausalAdmissionContext:
        raise ValueError("watch and admission must be exact causal providers")
    if type(baseline) is not ReplayProviderBaseline or not baseline._matches_providers(watch=watch, admission=admission):
        raise ValueError("provider baseline does not match causal providers")
    if watch.source._clock is not admission._clock:
        raise ValueError("watch and admission must share the same ReplayClock object")
    _validate_ledger_prefix(bundle, ledger, next_pass_index)
    watch_seed = watch.snapshot()
    admission_snapshot = admission.replay_snapshot()
    at = admission.decision_time
    _validate_checkpoint_clock(bundle, next_pass_index, at)
    if watch_seed.observed_at != at:
        raise ValueError("watch and admission clock times must match")
    state = {
        "bundle_fingerprint": bundle_fingerprint, "provider_baseline_fingerprint": baseline.fingerprint,
        "ledger": ledger.as_dict(),
        "ledger_digest": ledger.digest, "next_pass_index": next_pass_index,
        "clock_time": at.isoformat(), "watch": _seed_dict(watch_seed),
        "admission": admission_snapshot,
    }
    return deepcopy({"schema_version": _SCHEMA, "state": state, "checksum": canonical_digest(state)})


def restore_checkpoint(checkpoint, *, bundle, clock, baseline) -> RestoredReplayState:
    if type(checkpoint) is not dict or set(checkpoint) != {"schema_version", "state", "checksum"}:
        raise ValueError("checkpoint must have the canonical schema")
    if checkpoint["schema_version"] != _SCHEMA or type(checkpoint["state"]) is not dict:
        raise ValueError("unsupported checkpoint schema")
    state = checkpoint["state"]
    required = {"bundle_fingerprint", "provider_baseline_fingerprint", "ledger", "ledger_digest", "next_pass_index", "clock_time", "watch", "admission"}
    if set(state) != required or type(checkpoint["checksum"]) is not str:
        raise ValueError("checkpoint state is not canonical")
    if canonical_digest(state) != checkpoint["checksum"]:
        raise ValueError("checkpoint checksum does not match state")
    if state["bundle_fingerprint"] != _bundle_fingerprint(bundle):
        raise ValueError("bundle fingerprint does not match checkpoint")
    if type(baseline) is not ReplayProviderBaseline or state["provider_baseline_fingerprint"] != baseline.fingerprint:
        raise ValueError("provider baseline does not match checkpoint")
    ledger = _ledger_from_dict(state["ledger"])
    if ledger.run_id != bundle.run_id or ledger.digest != state["ledger_digest"]:
        raise ValueError("ledger digest does not match checkpoint")
    index = state["next_pass_index"]
    if type(index) is not int or index != len(ledger.records) or not 0 <= index <= len(bundle.anchors):
        raise ValueError("checkpoint next_pass_index is invalid")
    _validate_ledger_prefix(bundle, ledger, index)
    at = _time(state["clock_time"], "checkpoint clock_time")
    _validate_checkpoint_clock(bundle, index, at)
    _validate_binding(clock, at)
    if type(state["admission"]) is not dict:
        raise ValueError("checkpoint admission snapshot is invalid")
    admission_state = state["admission"].get("state")
    if type(admission_state) is not dict or admission_state.get("decision_time") != at.isoformat():
        raise ValueError("checkpoint admission clock does not match")
    watch_seed = _watch_seed(state["watch"])
    if watch_seed.observed_at != at or watch_seed.available_at != at:
        raise ValueError("checkpoint watch clock does not match")
    if not baseline._matches_checkpoint(
            watch=watch_seed, admission_snapshot=state["admission"], decision_time=at):
        raise ValueError("provider baseline does not match checkpoint evidence")
    watch = CausalWatchStorage(seed=watch_seed, decision_time=at, clock=clock)
    admission = CausalAdmissionContext.from_replay_snapshot(state["admission"], clock=clock)
    return RestoredReplayState(ledger=ledger, next_pass_index=index, watch=watch, admission=admission)


def _seed_dict(seed: WatchStateSeed) -> dict:
    return {"seed_id": seed.seed_id, "source": seed.source, "observed_at": seed.observed_at.isoformat(),
            "available_at": seed.available_at.isoformat(), "covered_through": seed.covered_through.isoformat(),
            "status": seed.status, "text": seed.text}


def _watch_seed(value) -> WatchStateSeed:
    if type(value) is not dict or set(value) != {"seed_id", "source", "observed_at", "available_at", "covered_through", "status", "text"}:
        raise ValueError("checkpoint watch snapshot is invalid")
    return WatchStateSeed(seed_id=value["seed_id"], source=value["source"],
        observed_at=_time(value["observed_at"], "watch observed_at"),
        available_at=_time(value["available_at"], "watch available_at"),
        covered_through=_time(value["covered_through"], "watch covered_through"),
        status=value["status"], text=value["text"])


def _seed_identity(seed) -> dict:
    if not isinstance(seed, WatchStateSeed) and not hasattr(seed, "seed_id"):
        raise ValueError("provider seed identity is invalid")
    return {
        "seed_id": seed.seed_id, "source": seed.source,
        "covered_through": seed.covered_through.isoformat(),
    }


def _suffix_index(full, remaining) -> int:
    if type(full) is not tuple or type(remaining) is not tuple or len(remaining) > len(full):
        raise ValueError("provider schedule is invalid")
    index = len(full) - len(remaining)
    if full[index:] != remaining:
        raise ValueError("provider schedule does not match trusted baseline")
    return index


def _validate_ledger_prefix(bundle: ReplayEvidenceBundle, ledger: ReplayRunLedger, index: int) -> None:
    for record_index, record in enumerate(ledger.records[:index]):
        anchor = bundle.anchors[record_index]
        expected_events = tuple(event.event_id for event in bundle.events_before_or_at(anchor.decision_time))
        if record.pass_id != anchor.pass_id or record.decision_time != anchor.decision_time:
            raise ValueError(f"ledger record {record_index} does not match bundle anchor")
        if record.consumed_event_ids != expected_events:
            raise ValueError(f"ledger record {record_index} does not match consumed bundle events")


def _validate_checkpoint_clock(bundle: ReplayEvidenceBundle, index: int, at: datetime) -> None:
    if index and at < bundle.anchors[index - 1].decision_time:
        raise ValueError("checkpoint clock cannot precede last consumed anchor")


def _ledger_from_dict(value) -> ReplayRunLedger:
    if type(value) is not dict or set(value) != {"run_id", "records"} or type(value["records"]) is not list:
        raise ValueError("checkpoint ledger is invalid")
    records = []
    for row in value["records"]:
        if type(row) is not dict:
            raise ValueError("checkpoint ledger record is invalid")
        try:
            records.append(ReplayPassRecord(pass_index=row["pass_index"], pass_id=row["pass_id"],
                decision_time=_time(row["decision_time"], "ledger decision_time"), outcome=row["outcome"],
                consumed_event_ids=tuple(row["consumed_event_ids"]), activation_state=row["activation_state"],
                candidate=row["candidate"], lifecycle_messages=tuple(tuple(item) for item in row["lifecycle_messages"]),
                diagnostics=tuple(row["diagnostics"]), predecessor_digest=row["predecessor_digest"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("checkpoint ledger record is invalid") from exc
    return ReplayRunLedger(run_id=value["run_id"], records=tuple(records))


def _time(value, field):
    if type(value) is not str:
        raise ValueError(f"{field} must be an ISO timestamp")
    fraction = re.match(r"^\d{4}(?:-\d{2}-\d{2}|\d{4})[Tt ]\d{2}:?\d{2}:?\d{2}[.,](\d+)", value)
    if fraction is not None and len(fraction.group(1)) > 6:
        raise ValueError(f"{field} must be microsecond-exact")
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")), field)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc

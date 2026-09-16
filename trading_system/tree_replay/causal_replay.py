"""Deterministic supplied-evidence closed-bar replay observations only.

This runner deliberately records selected internal-reversal plans without
registering them with the tracker.  Existing supplied tracker rows advance via
the accepted closed lifecycle components; no new row, delivery, economics, or
dataset action is available here.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from .admission_context import CausalAdmissionContext
from .causal_replay_checkpoint import (
    ReplayProviderBaseline,
    checkpoint_from,
    restore_checkpoint,
)
from .causal_replay_contracts import (
    canonical_evidence_digest,
    ReplayEvidenceBundle,
    ReplayPassAnchor,
    ReplayPassRecord,
    ReplayRunLedger,
)
from .clock import ReplayClock, _validate_binding
from .outer_admission import OuterAdmissionAdapter
from .outer_admission_contracts import OuterAdmissionInputs
from .lifecycle_caller import TrackerLifecycleCaller
from ._vendor.lifecycle_closed_resolver import LifecycleClosedResolver
from .reversal_producer import (
    ReversalFrameRequest,
    _evaluate_reversal_asof,
)
from .levelmap import MapFrameRequest
from .watch_storage import CausalWatchStorage


_SUPPORTED_VARIANT = "level_reversal:5m"


@dataclass(frozen=True, kw_only=True)
class InternalReversalInputs:
    """Exact supplied input image for one internal-reversal anchor."""

    snapshot_id: str
    map_requests: tuple[MapFrameRequest, ...]
    reversal_requests: tuple[ReversalFrameRequest, ...]


class _TextWriter:
    def __init__(self, consume):
        self._consume = consume

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def write(self, text):
        self._consume(text)


class _LifecycleTape:
    """Private memory-only ports required by the accepted lifecycle caller.

    The causal admission context remains the sole source for tracker state,
    frames, and clock.  The remaining lifecycle persistence ports have no
    supplied replay artifact in this slice, so they are isolated in memory and
    cannot deliver or write a filesystem artifact.
    """

    def __init__(self, admission: CausalAdmissionContext):
        self._admission = admission
        self._journal = ""
        self._outcomes: list[dict[str, object]] = []
        self._files: dict[str, str] = {}
        self._tmp: dict[str, str] = {}
        self._next_fd = 0

    def load(self):
        return self._admission.load()

    def save(self, state):
        return self._admission.save(state)

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        return self._admission.fetch_corrected(symbol, timeframe, lookback_days)

    def now_epoch(self):
        return self._admission.now_epoch()

    def now_utc(self):
        return datetime.fromtimestamp(self.now_epoch(), timezone.utc)

    def outcomes_mkdir(self, _path, *, parents, exist_ok):
        if parents is not True or exist_ok is not True:
            raise ValueError("lifecycle outcome directory call is not canonical")

    def open_outcomes(self, mode, *, encoding):
        if mode != "a" or encoding != "utf-8":
            raise ValueError("lifecycle outcome write is not canonical")
        return _TextWriter(lambda text: self._outcomes.append(json.loads(text)))

    def journal_exists(self):
        return bool(self._journal)

    def journal_text(self, *, encoding):
        if encoding != "utf-8":
            raise ValueError("journal encoding must be utf-8")
        return self._journal

    def mkdir(self, _path, *, parents, exist_ok):
        if parents is not True or exist_ok is not True:
            raise ValueError("journal directory call is not canonical")

    @contextmanager
    def open_append_lock(self, _path, mode):
        if mode != "a+":
            raise ValueError("append lock mode must be a+")
        yield object()

    def try_acquire(self, _handle, *, timeout):
        if timeout is not None:
            raise ValueError("lifecycle journal append must use its supplied blocking lock")
        return True

    def release(self, _handle):
        return None

    def assert_offline(self):
        return None

    def open_journal(self, mode, *, encoding):
        if mode != "a" or encoding != "utf-8":
            raise ValueError("journal write is not canonical")
        return _TextWriter(lambda text: setattr(self, "_journal", self._journal + text))

    def park_exists(self):
        return False

    def park_text(self, *, encoding):
        if encoding != "utf-8":
            raise ValueError("park encoding must be utf-8")
        return "{}"

    def shelf_exists(self):
        return False

    def shelf_text(self, *, encoding):
        if encoding != "utf-8":
            raise ValueError("shelf encoding must be utf-8")
        return "{}"

    def queue_exists(self, _path):
        return False

    def queue_text(self, _path, *, encoding):
        if encoding != "utf-8":
            raise ValueError("queue encoding must be utf-8")
        raise FileNotFoundError("no supplied queue evidence")

    def receipt_stat(self):
        raise OSError("no supplied delivery receipt evidence")

    def receipt_text(self, *, encoding):
        if encoding != "utf-8":
            raise ValueError("receipt encoding must be utf-8")
        raise OSError("no supplied delivery receipt evidence")

    def atomic_mkdir(self, _path, *, parents, exist_ok):
        if parents is not True or exist_ok is not True:
            raise ValueError("atomic directory call is not canonical")

    def atomic_mkstemp(self, _path, *, suffix):
        if suffix != ".tmp":
            raise ValueError("atomic temporary suffix is not canonical")
        self._next_fd += 1
        name = f"memory-{self._next_fd}{suffix}"
        self._tmp[name] = ""
        return self._next_fd, name

    def atomic_fdopen(self, fd, mode, *, encoding):
        if type(fd) is not int or mode != "w" or encoding != "utf-8":
            raise ValueError("atomic write is not canonical")
        name = f"memory-{fd}.tmp"
        return _TextWriter(lambda text: self._tmp.__setitem__(name, self._tmp[name] + text))

    def atomic_fsync(self, _handle):
        return None

    def atomic_replace(self, source, target):
        self._files[target] = self._tmp.pop(source)

    def atomic_unlink(self, path):
        self._tmp.pop(path, None)


class ClosedBarCausalReplay:
    """Run the accepted closed-bar order against immutable supplied evidence."""

    def __init__(self, bundle, *, clock, watch, admission, reversal_inputs,
                 outer_admission_inputs=None, baseline=None):
        if type(bundle) is not ReplayEvidenceBundle:
            raise ValueError("bundle must be an exact ReplayEvidenceBundle")
        if type(clock) is not ReplayClock:
            raise ValueError("clock must be an exact ReplayClock")
        if type(watch) is not CausalWatchStorage or type(admission) is not CausalAdmissionContext:
            raise ValueError("watch and admission must be exact causal providers")
        _validate_binding(clock, admission.decision_time)
        if watch.source._clock is not clock or admission._clock is not clock:
            raise ValueError("watch and admission must share the supplied ReplayClock object")
        if not isinstance(reversal_inputs, Mapping):
            raise ValueError("reversal_inputs must be an exact pass-ID mapping")
        if outer_admission_inputs is not None and not isinstance(outer_admission_inputs, Mapping):
            raise ValueError("outer_admission_inputs must be a pass-ID mapping or None")
        if baseline is None:
            baseline = ReplayProviderBaseline.capture(watch=watch, admission=admission)
        if type(baseline) is not ReplayProviderBaseline:
            raise ValueError("baseline must be an exact ReplayProviderBaseline")
        self.bundle = bundle
        self.clock = clock
        self.watch = watch
        self.admission = admission
        self.reversal_inputs = dict(reversal_inputs)
        self.outer_admission_inputs = (
            None if outer_admission_inputs is None else dict(outer_admission_inputs)
        )
        self.baseline = baseline
        self._ledger = ReplayRunLedger.empty(bundle.run_id)
        self._next_pass_index = 0

    @property
    def ledger(self):
        return self._ledger

    def _append(self, anchor: ReplayPassAnchor, *, outcome: str, candidate, messages, diagnostics):
        commitments = tuple(event.commitment() for event in self.bundle.events_before_or_at(anchor.decision_time))
        evidence_diagnostic = {
            "stage": "evidence_binding",
            "consumed_event_commitments": [commitment.as_dict() for commitment in commitments],
            "provider_baseline_fingerprint": self.baseline.fingerprint,
        }
        record = ReplayPassRecord(
            pass_index=self._next_pass_index,
            pass_id=anchor.pass_id,
            decision_time=anchor.decision_time,
            outcome=outcome,
            consumed_event_ids=tuple(event.event_id for event in self.bundle.events_before_or_at(anchor.decision_time)),
            activation_state=anchor.activation_state(),
            candidate=candidate,
            lifecycle_messages=tuple(messages),
            diagnostics=tuple(diagnostics) + (evidence_diagnostic,),
            predecessor_digest=self._ledger.next_predecessor_digest,
        )
        self._ledger = self._ledger.append(record)
        self._next_pass_index += 1

    def _blocked(self, anchor, *, stage, blocker, exception=None):
        diagnostic: dict[str, object] = {"stage": stage, "blocker": blocker}
        if exception is not None:
            diagnostic["exception_type"] = type(exception).__name__
        self._append(anchor, outcome="BLOCKED", candidate=None, messages=(), diagnostics=(diagnostic,))

    def _required_events_available(self, anchor):
        by_id = {event.event_id: event for event in self.bundle.events}
        missing = [event_id for event_id in anchor.required_event_ids
                   if event_id not in by_id or by_id[event_id].available_at > anchor.decision_time]
        return missing

    def _inputs(self, anchor):
        inputs = self.reversal_inputs.get(anchor.pass_id)
        if type(inputs) is not InternalReversalInputs:
            raise ValueError("INTERNAL_REVERSAL_INPUT_MISSING_OR_INVALID")
        if type(inputs.snapshot_id) is not str or not inputs.snapshot_id:
            raise ValueError("INTERNAL_REVERSAL_SNAPSHOT_INVALID")
        if type(inputs.map_requests) is not tuple or type(inputs.reversal_requests) is not tuple:
            raise ValueError("INTERNAL_REVERSAL_REQUESTS_INVALID")
        return inputs

    def _outer_inputs(self, anchor):
        if self.outer_admission_inputs is None:
            return None
        inputs = self.outer_admission_inputs.get(anchor.pass_id)
        if type(inputs) is not OuterAdmissionInputs:
            raise ValueError("OUTER_ADMISSION_INPUT_MISSING_OR_INVALID")
        return inputs

    @staticmethod
    def _publication_kind(channel: str) -> str:
        return {
            "frames": "FRAME_PUBLICATION", "tracker": "TRACKER_PUBLICATION",
            "quotes": "BAR_PUBLICATION", "watch_log": "WATCH_PUBLICATION",
            "busy": "ACTIVATION_PUBLICATION",
        }[channel]

    def _validate_bound_evidence(self, anchor: ReplayPassAnchor):
        """Prove every provider input before the context clock/provider can be used."""
        inputs = self._inputs(anchor)
        eligible = self.bundle.events_before_or_at(anchor.decision_time)
        by_id = {event.event_id: event for event in self.bundle.events}
        if len(anchor.required_event_ids) != 1:
            raise ValueError("REQUIRED_INTERNAL_REVERSAL_BINDING_NOT_UNIQUE")
        required_event = by_id[anchor.required_event_ids[0]]
        required_binding = required_event.commitment()
        expected_input_digest = canonical_evidence_digest(inputs)
        if (
            required_event.available_at > anchor.decision_time
            or required_binding.consumer != "INTERNAL_REVERSAL_INPUT"
            or required_binding.artifact_id != anchor.pass_id
            or required_binding.artifact_digest != expected_input_digest
        ):
            raise ValueError("REQUIRED_EVENT_UNAVAILABLE")

        def unique_binding(consumer, artifact_id):
            matches = []
            for event in eligible:
                commitment = event.commitment()
                if commitment.consumer == consumer and commitment.artifact_id == artifact_id:
                    matches.append((event, commitment))
            if len(matches) != 1:
                raise ValueError("EVENT_BINDING_MISSING_OR_MISMATCH")
            return matches[0]

        reversal_event, reversal_binding = unique_binding("INTERNAL_REVERSAL_INPUT", anchor.pass_id)
        if (
            reversal_event.event_id != required_event.event_id
            or reversal_binding.artifact_digest != expected_input_digest
        ):
            raise ValueError("EVENT_BINDING_MISSING_OR_MISMATCH")
        if reversal_event.available_at > anchor.decision_time:
            raise ValueError("EVENT_BINDING_MISSING_OR_MISMATCH")

        for publication in self.admission.replay_publications_through(anchor.decision_time):
            event, binding = unique_binding("ADMISSION_PUBLICATION", publication.publication_id)
            if (
                event.kind != self._publication_kind(publication.channel)
                or event.available_at != publication.available_at
                or binding.artifact_digest != canonical_evidence_digest(publication)
            ):
                raise ValueError("EVENT_BINDING_MISSING_OR_MISMATCH")
        outer_inputs = None
        if self.outer_admission_inputs is not None and anchor.activation_state() == "EVIDENCED_ENABLED":
            outer_inputs = self._outer_inputs(anchor)
            outer_event, outer_binding = unique_binding("OUTER_ADMISSION_INPUT", anchor.pass_id)
            if (
                outer_event.available_at != outer_inputs.available_at
                or outer_event.available_at > anchor.decision_time
                or outer_binding.artifact_digest != canonical_evidence_digest(outer_inputs)
            ):
                raise ValueError("OUTER_ADMISSION_EVENT_BINDING_MISSING_OR_MISMATCH")
        return inputs, outer_inputs

    @staticmethod
    def _candidate(report):
        selected = report.get("selected")
        if type(selected) is not dict:
            raise ValueError("SELECTED_CANDIDATE_INVALID")
        return deepcopy(selected)

    def _run_anchor(self, anchor):
        if anchor.source_variant != _SUPPORTED_VARIANT:
            self._append(anchor, outcome="UNSUPPORTED", candidate=None, messages=(), diagnostics=(
                {"stage": "variant", "blocker": "SOURCE_VARIANT_UNSUPPORTED", "source_variant": anchor.source_variant},
            ))
            return
        try:
            inputs, outer_inputs = self._validate_bound_evidence(anchor)
        except Exception as exc:
            self._blocked(anchor, stage="evidence", blocker="EVENT_BINDING_MISSING_OR_MISMATCH", exception=exc)
            return

        try:
            self.admission.advance_to(anchor.decision_time)
        except Exception as exc:
            self._blocked(anchor, stage="clock", blocker="CONTEXT_ADVANCE_FAILED", exception=exc)
            return

        messages: tuple[tuple[str, bool], ...] = ()
        try:
            watch_state = self.watch.load()
            self.watch.save_before_producers(watch_state)
            lifecycle = _LifecycleTape(self.admission)
            messages = tuple(TrackerLifecycleCaller(lifecycle).check(
                lambda state: LifecycleClosedResolver(lifecycle).resolve(
                    state, now=self.admission.now_epoch(),
                )
            ))
        except Exception as exc:
            self._blocked(anchor, stage="lifecycle", blocker="LIFECYCLE_EVIDENCE_OR_RESOLUTION_ERROR", exception=exc)
            return

        try:
            evaluation = _evaluate_reversal_asof(
                snapshot_id=inputs.snapshot_id, instrument=self.bundle.instrument,
                decision_time=anchor.decision_time, map_requests=inputs.map_requests,
                reversal_requests=inputs.reversal_requests,
            )
            report = evaluation.report
            if type(report) is not dict:
                raise ValueError("PRODUCER_REPORT_INVALID")
        except Exception as exc:
            self._blocked(anchor, stage="producer", blocker="PRODUCER_ERROR", exception=exc)
            return

        status = report.get("status")
        diagnostic = {
            "stage": "producer", "status": status,
            "blocker": report.get("blocker"), "reason": report.get("reason"),
            "decision_id": report.get("decision_id"), "evaluation_sha256": report.get("evaluation_sha256"),
        }
        if status == "PRODUCER_SELECTED_UNADMITTED":
            try:
                candidate = self._candidate(report)
            except Exception as exc:
                self._blocked(anchor, stage="producer", blocker="SELECTED_CANDIDATE_INVALID", exception=exc)
                return
            admission_diagnostic: dict[str, object]
            outcome = "OBSERVE_ONLY"
            if outer_inputs is None:
                admission_diagnostic = {"stage": "admission", "blocker": "OUTER_ADMISSION_UNBOUND"}
            else:
                try:
                    decision = OuterAdmissionAdapter(admission=self.admission).evaluate(
                        outer_inputs, evaluation.selected_plan, active_reversals={},
                        watch_state=watch_state, record_alerts_enabled=True,
                    )
                except Exception as exc:
                    self._blocked(anchor, stage="admission", blocker="OUTER_ADMISSION_ERROR", exception=exc)
                    return
                outcome = decision.status
                admission_diagnostic = {"stage": "admission", **decision.as_dict()}
            try:
                self.watch.save_final(watch_state)
            except Exception as exc:
                self._blocked(anchor, stage="watch_final_save", blocker="WATCH_FINAL_SAVE_FAILED", exception=exc)
                return
            self._append(anchor, outcome=outcome, candidate=candidate, messages=messages,
                         diagnostics=(diagnostic, admission_diagnostic))
        elif status == "NO_CANDIDATE":
            try:
                self.watch.save_final(watch_state)
            except Exception as exc:
                self._blocked(anchor, stage="watch_final_save", blocker="WATCH_FINAL_SAVE_FAILED", exception=exc)
                return
            self._append(anchor, outcome="NO_CANDIDATE", candidate=None, messages=messages, diagnostics=(diagnostic,))
        else:
            try:
                self.watch.save_final(watch_state)
            except Exception as exc:
                self._blocked(anchor, stage="watch_final_save", blocker="WATCH_FINAL_SAVE_FAILED", exception=exc)
                return
            self._append(anchor, outcome="BLOCKED", candidate=None, messages=messages, diagnostics=(diagnostic,))

    def run_until(self, pass_count: int):
        if type(pass_count) is not int or not self._next_pass_index <= pass_count <= len(self.bundle.anchors):
            raise ValueError("pass_count must be a legal total bundle prefix")
        while self._next_pass_index < pass_count:
            self._run_anchor(self.bundle.anchors[self._next_pass_index])
        checkpoint = checkpoint_from(
            bundle=self.bundle, ledger=self._ledger, next_pass_index=self._next_pass_index,
            watch=self.watch, admission=self.admission, baseline=self.baseline,
        )
        return self._ledger, checkpoint

    def run(self):
        while self._next_pass_index < len(self.bundle.anchors):
            self._run_anchor(self.bundle.anchors[self._next_pass_index])
        return self._ledger

    @classmethod
    def restore(cls, checkpoint, *, bundle, clock, baseline, reversal_inputs,
                outer_admission_inputs=None):
        restored = restore_checkpoint(checkpoint, bundle=bundle, clock=clock, baseline=baseline)
        replay = cls(
            bundle, clock=clock, watch=restored.watch, admission=restored.admission,
            reversal_inputs=reversal_inputs, outer_admission_inputs=outer_admission_inputs,
            baseline=baseline,
        )
        replay._ledger = restored.ledger
        replay._next_pass_index = restored.next_pass_index
        return replay

"""Immutable, payload-free evidence contracts for outer source admission."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from .bars import _utc
from .state import _identity


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SUPPORTED_SOURCE_VARIANT = "level_reversal:5m"
_DECISION_STATUSES = frozenset({
    "ADMITTED_TRACKER", "REJECTED", "OBSERVE_ONLY", "BLOCKED", "UNSUPPORTED",
})


@dataclass(frozen=True, kw_only=True)
class AdmissionEvidenceRef:
    """One immutable reference to supplied admission evidence, never its payload."""

    event_id: str
    artifact_id: str
    source_id: str
    artifact_digest: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime

    def __post_init__(self) -> None:
        _identity(self.event_id, "event_id")
        _identity(self.artifact_id, "artifact_id")
        _identity(self.source_id, "source_id")
        if type(self.artifact_digest) is not str or not _SHA256.fullmatch(self.artifact_digest):
            raise ValueError("artifact_digest must be a SHA-256 digest")
        for field in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.covered_through < self.available_at:
            raise ValueError("covered_through cannot precede available_at")

    def as_dict(self) -> dict[str, str]:
        return {
            "event_id": self.event_id,
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "artifact_digest": self.artifact_digest,
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "covered_through": self.covered_through.isoformat(),
        }


@dataclass(frozen=True, kw_only=True)
class OuterAdmissionInputs:
    """Causal input commitments for one source outer-admission evaluation."""

    input_id: str
    source_variant: str
    episode_id: str
    plan_id: str
    plan_digest: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    evidence: tuple[AdmissionEvidenceRef, ...]

    def __post_init__(self) -> None:
        for field in ("input_id", "source_variant", "episode_id", "plan_id"):
            _identity(getattr(self, field), field)
        if self.source_variant != _SUPPORTED_SOURCE_VARIANT:
            raise ValueError("source_variant must be level_reversal:5m")
        if type(self.plan_digest) is not str or not _SHA256.fullmatch(self.plan_digest):
            raise ValueError("plan_digest must be a SHA-256 digest")
        for field in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.covered_through < self.available_at:
            raise ValueError("covered_through cannot precede available_at")
        if type(self.evidence) is not tuple or not self.evidence:
            raise ValueError("evidence must be a nonempty immutable tuple")
        if any(type(item) is not AdmissionEvidenceRef for item in self.evidence):
            raise ValueError("evidence must contain exact AdmissionEvidenceRef objects")
        event_ids = tuple(item.event_id for item in self.evidence)
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("evidence cannot reuse an event_id")
        if any(item.available_at > self.available_at for item in self.evidence):
            raise ValueError("evidence cannot be available after available_at")

    def as_dict(self) -> dict[str, object]:
        return {
            "input_id": self.input_id,
            "source_variant": self.source_variant,
            "episode_id": self.episode_id,
            "plan_id": self.plan_id,
            "plan_digest": self.plan_digest,
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "covered_through": self.covered_through.isoformat(),
            "evidence": [item.as_dict() for item in self.evidence],
        }


@dataclass(frozen=True, kw_only=True)
class OuterAdmissionDecision:
    """Detached source-admission fact, explicitly distinct from a trade outcome."""

    decision_id: str
    input_id: str
    status: str
    gate_trace: tuple[str, ...]
    reason: str | None
    tracker_id: str | None
    tracker_state_digest: str | None
    annotations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in ("decision_id", "input_id"):
            _identity(getattr(self, field), field)
        if type(self.status) is not str or self.status not in _DECISION_STATUSES:
            raise ValueError("status must be an explicit outer-admission status")
        if type(self.gate_trace) is not tuple or not self.gate_trace:
            raise ValueError("gate_trace must be a nonempty immutable tuple")
        for gate in self.gate_trace:
            _identity(gate, "gate_trace")
        if self.reason is not None:
            _identity(self.reason, "reason")
        if type(self.annotations) is not tuple:
            raise ValueError("annotations must be an immutable tuple")
        for annotation in self.annotations:
            _identity(annotation, "annotations")
        admitted = self.status == "ADMITTED_TRACKER"
        tracker_fields_present = type(self.tracker_id) is str and type(self.tracker_state_digest) is str
        tracker_fields_absent = self.tracker_id is None and self.tracker_state_digest is None
        if not tracker_fields_present and not tracker_fields_absent:
            raise ValueError("tracker identity must be complete or absent")
        if admitted != tracker_fields_present:
            raise ValueError("tracker identity is required only for ADMITTED_TRACKER")
        if tracker_fields_present:
            _identity(self.tracker_id, "tracker_id")
            if not _SHA256.fullmatch(self.tracker_state_digest):
                raise ValueError("tracker_state_digest must be a SHA-256 digest")

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "input_id": self.input_id,
            "status": self.status,
            "gate_trace": list(self.gate_trace),
            "reason": self.reason,
            "tracker_id": self.tracker_id,
            "tracker_state_digest": self.tracker_state_digest,
            "annotations": list(self.annotations),
        }

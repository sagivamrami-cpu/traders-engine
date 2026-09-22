"""Immutable, supplied-evidence contracts for the closed-bar replay spine.

These are deliberately data-only contracts.  They neither read a feed nor
create tracker rows, outcomes, economic labels, datasets, models, or live work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from .bars import _number, _utc, _validate_identity
from .state import _identity


_EVENT_KINDS = frozenset({
    "BAR_PUBLICATION",
    "FRAME_PUBLICATION",
    "WATCH_PUBLICATION",
    "TRACKER_PUBLICATION",
    "ACTIVATION_PUBLICATION",
})
_OUTCOMES = frozenset({
    "OBSERVE_ONLY", "NO_CANDIDATE", "BLOCKED", "SKIPPED", "UNSUPPORTED",
    "REJECTED", "ADMITTED_TRACKER",
})
_ACTIVATION_STATES = frozenset({
    "EVIDENCED_ENABLED", "EVIDENCED_DISABLED", "MISMATCHED_VARIANT",
    "NOT_YET_AVAILABLE", "COVERAGE_EXPIRED",
})
_FORBIDDEN_STRUCTURED_FIELDS = frozenset({"net_pnl", "net_R", "success", "failure"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BINDING_CONSUMERS = frozenset({
    "ADMISSION_PUBLICATION", "INTERNAL_REVERSAL_INPUT", "OUTER_ADMISSION_INPUT",
})
_EVIDENCE_DIAGNOSTIC_STAGE = "evidence_binding"


def _canonical_value(value: object, *, field: str) -> object:
    """Return a detached immutable JSON-shaped value or fail closed."""
    if value is None or type(value) is bool or type(value) is str:
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeError as exc:
                raise ValueError(f"{field} must contain UTF-8 text") from exc
        return value
    if type(value) in (int, float):
        _number(value, field)
        return value
    if type(value) in (list, tuple):
        return tuple(_canonical_value(item, field=field) for item in value)
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{field} must contain string JSON keys")
            try:
                key.encode("utf-8")
            except UnicodeError as exc:
                raise ValueError(f"{field} must contain UTF-8 JSON keys") from exc
            result[key] = _canonical_value(item, field=field)
        return MappingProxyType(result)
    raise ValueError(f"{field} must contain finite JSON-compatible values")


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_value(item) for item in value]
    return value


def canonical_digest(value: object) -> str:
    """Hash only finite, recursively JSON-compatible values canonically."""
    try:
        normalized = _json_value(_canonical_value(value, field="value"))
        encoded = json.dumps(
            normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("value must contain finite JSON-compatible values") from exc
    return hashlib.sha256(encoded).hexdigest()


def _evidence_value(value: object) -> object:
    """Encode supplied provider values without repr() or object identity."""
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": _utc(value, "evidence datetime").isoformat()}
    if value is None or type(value) is bool or type(value) is str:
        return _json_value(_canonical_value(value, field="evidence"))
    if type(value) in (int, float):
        return _json_value(_canonical_value(value, field="evidence"))
    if type(value) is tuple:
        return {"__type__": "tuple", "items": [_evidence_value(item) for item in value]}
    if type(value) is list:
        return {"__type__": "list", "items": [_evidence_value(item) for item in value]}
    if isinstance(value, Mapping):
        items: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("evidence mappings require string keys")
            key.encode("utf-8")
            items[key] = _evidence_value(item)
        return {"__type__": "mapping", "items": items}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {field.name: _evidence_value(getattr(value, field.name)) for field in fields(value)},
        }
    raise ValueError("evidence contains unsupported value")


def canonical_evidence_digest(value: object) -> str:
    """Deterministically fingerprint nested supplied provider evidence."""
    try:
        encoded = json.dumps(
            _evidence_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("evidence must contain canonical supported values") from exc
    return hashlib.sha256(encoded).hexdigest()


def _event_binding(payload: Mapping[str, object]) -> tuple[str | None, str | None, str | None]:
    if "evidence_binding" not in payload:
        return None, None, None
    binding = payload["evidence_binding"]
    if not isinstance(binding, Mapping) or set(binding) != {"consumer", "artifact_id", "artifact_digest"}:
        raise ValueError("evidence_binding must have exact consumer, artifact_id, artifact_digest fields")
    consumer, artifact_id, artifact_digest = (
        binding["consumer"], binding["artifact_id"], binding["artifact_digest"],
    )
    if type(consumer) is not str or consumer not in _BINDING_CONSUMERS:
        raise ValueError("evidence_binding consumer is unsupported")
    _identity(artifact_id, "evidence_binding artifact_id")
    if type(artifact_digest) is not str or not _SHA256.fullmatch(artifact_digest):
        raise ValueError("evidence_binding artifact_digest must be a SHA-256 digest")
    return consumer, artifact_id, artifact_digest


def _identity_tuple(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field} must be an immutable tuple")
    result = []
    for item in value:
        _identity(item, field)
        result.append(item)
    if len(set(result)) != len(result):
        raise ValueError(f"{field} cannot contain duplicates")
    return tuple(result)


def _payload_available_at(payload: Mapping[str, object], available_at: datetime) -> None:
    if "available_at" not in payload:
        raise ValueError("event payload must declare payload availability")
    declared = payload["available_at"]
    if type(declared) is not str:
        raise ValueError("event payload availability must be an ISO timestamp")
    if any(len(fraction) > 6 for fraction in re.findall(r"[.,](\d+)", declared[10:])):
        raise ValueError("event payload availability must be microsecond-exact")
    try:
        parsed = datetime.fromisoformat(declared.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("event payload availability must be an ISO timestamp") from exc
    if _utc(parsed, "payload available_at") != available_at:
        raise ValueError("event payload availability must equal event available_at")


def _contains_forbidden_structured_field(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in _FORBIDDEN_STRUCTURED_FIELDS or _contains_forbidden_structured_field(item)
            for key, item in value.items()
        )
    if type(value) is tuple:
        return any(_contains_forbidden_structured_field(item) for item in value)
    return False


@dataclass(frozen=True, kw_only=True)
class TrackerActivationEvidence:
    evidence_id: str
    source: str
    variant: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    enabled: bool

    def __post_init__(self) -> None:
        for field in ("evidence_id", "source", "variant"):
            _identity(getattr(self, field), field)
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be an explicit bool")
        for field in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.covered_through < self.available_at:
            raise ValueError("covered_through cannot precede available_at")

    def state_at(self, *, decision_time: datetime, variant: str) -> str:
        at = _utc(decision_time, "decision_time")
        _identity(variant, "variant")
        if variant != self.variant:
            return "MISMATCHED_VARIANT"
        if at < self.available_at:
            return "NOT_YET_AVAILABLE"
        if at > self.covered_through:
            return "COVERAGE_EXPIRED"
        return "EVIDENCED_ENABLED" if self.enabled else "EVIDENCED_DISABLED"


@dataclass(frozen=True, kw_only=True)
class ReplayEvent:
    event_id: str
    available_at: datetime
    sequence: int
    kind: str
    source: str
    variant: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        for field in ("event_id", "source", "variant"):
            _identity(getattr(self, field), field)
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a native nonnegative integer")
        if type(self.kind) is not str or self.kind not in _EVENT_KINDS:
            raise ValueError("unknown event kind")
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a JSON object")
        payload = _canonical_value(self.payload, field="payload")
        assert isinstance(payload, Mapping)
        if _contains_forbidden_structured_field(payload):
            raise ValueError("payload contains forbidden economic or outcome fields")
        _payload_available_at(payload, self.available_at)
        _event_binding(payload)
        object.__setattr__(self, "payload", payload)

    def commitment(self) -> ReplayEventCommitment:
        consumer, artifact_id, artifact_digest = _event_binding(self.payload)
        return ReplayEventCommitment(
            event_id=self.event_id, available_at=self.available_at, sequence=self.sequence,
            payload_digest=canonical_digest(self.payload), consumer=consumer,
            artifact_id=artifact_id, artifact_digest=artifact_digest,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id, "available_at": self.available_at.isoformat(),
            "sequence": self.sequence, "kind": self.kind, "source": self.source,
            "variant": self.variant, "payload": _json_value(self.payload),
        }


@dataclass(frozen=True, kw_only=True)
class ReplayEventCommitment:
    """Raw-payload-free immutable commitment for one eligible bundle event."""

    event_id: str
    available_at: datetime
    sequence: int
    payload_digest: str
    consumer: str | None
    artifact_id: str | None
    artifact_digest: str | None

    def __post_init__(self) -> None:
        _identity(self.event_id, "event_id")
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a native nonnegative integer")
        if type(self.payload_digest) is not str or not _SHA256.fullmatch(self.payload_digest):
            raise ValueError("payload_digest must be a SHA-256 digest")
        fields_are_absent = self.consumer is self.artifact_id is self.artifact_digest is None
        fields_are_present = (
            type(self.consumer) is str and self.consumer in _BINDING_CONSUMERS
            and type(self.artifact_id) is str and type(self.artifact_digest) is str
        )
        if not fields_are_absent and not fields_are_present:
            raise ValueError("commitment binding must be all-or-nothing")
        if fields_are_present:
            _identity(self.artifact_id, "commitment artifact_id")
            if not _SHA256.fullmatch(self.artifact_digest):
                raise ValueError("commitment artifact_digest must be a SHA-256 digest")

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id, "available_at": self.available_at.isoformat(),
            "sequence": self.sequence, "payload_digest": self.payload_digest,
            "consumer": self.consumer, "artifact_id": self.artifact_id,
            "artifact_digest": self.artifact_digest,
        }


@dataclass(frozen=True, kw_only=True)
class ReplayPassAnchor:
    pass_id: str
    decision_time: datetime
    source_variant: str
    required_event_ids: tuple[str, ...]
    activation: TrackerActivationEvidence

    def __post_init__(self) -> None:
        _identity(self.pass_id, "pass_id")
        _identity(self.source_variant, "source_variant")
        object.__setattr__(self, "decision_time", _utc(self.decision_time, "decision_time"))
        object.__setattr__(self, "required_event_ids", _identity_tuple(self.required_event_ids, "required_event_ids"))
        if type(self.activation) is not TrackerActivationEvidence:
            raise ValueError("activation must be an exact TrackerActivationEvidence")

    def activation_state(self) -> str:
        return self.activation.state_at(
            decision_time=self.decision_time, variant=self.source_variant,
        )


@dataclass(frozen=True, kw_only=True)
class ReplayEvidenceBundle:
    run_id: str
    instrument: str
    events: tuple[ReplayEvent, ...]
    anchors: tuple[ReplayPassAnchor, ...]

    def __post_init__(self) -> None:
        _identity(self.run_id, "run_id")
        _validate_identity(self.instrument, "5m")
        if self.instrument != "OANDA:XAUUSD":
            raise ValueError("instrument must be exact OANDA:XAUUSD")
        if type(self.events) is not tuple:
            raise ValueError("events must be an immutable tuple")
        if type(self.anchors) is not tuple:
            raise ValueError("anchors must be an immutable tuple")
        event_ids: set[str] = set()
        previous_key: tuple[datetime, int] | None = None
        for replay_event in self.events:
            if type(replay_event) is not ReplayEvent:
                raise ValueError("events must contain exact ReplayEvent objects")
            if replay_event.event_id in event_ids:
                raise ValueError("duplicate event_id")
            event_ids.add(replay_event.event_id)
            key = (replay_event.available_at, replay_event.sequence)
            if previous_key is not None and key <= previous_key:
                raise ValueError("events must be strictly increasing by available_at and sequence")
            previous_key = key
        pass_ids: set[str] = set()
        previous_time: datetime | None = None
        for replay_anchor in self.anchors:
            if type(replay_anchor) is not ReplayPassAnchor:
                raise ValueError("anchors must contain exact ReplayPassAnchor objects")
            if replay_anchor.pass_id in pass_ids:
                raise ValueError("duplicate pass_id")
            pass_ids.add(replay_anchor.pass_id)
            if previous_time is not None and replay_anchor.decision_time <= previous_time:
                raise ValueError("anchors must be strictly increasing by decision_time")
            previous_time = replay_anchor.decision_time
            missing = set(replay_anchor.required_event_ids) - event_ids
            if missing:
                raise ValueError("anchor required_event_ids must exist in events")

    def events_before_or_at(self, at: datetime) -> tuple[ReplayEvent, ...]:
        decision_time = _utc(at, "at")
        return tuple(event for event in self.events if event.available_at <= decision_time)

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id, "instrument": self.instrument,
            "events": [event.as_dict() for event in self.events],
            "anchors": [
                {
                    "pass_id": anchor.pass_id,
                    "decision_time": anchor.decision_time.isoformat(),
                    "source_variant": anchor.source_variant,
                    "required_event_ids": list(anchor.required_event_ids),
                    "activation_state": anchor.activation_state(),
                }
                for anchor in self.anchors
            ],
        }


@dataclass(frozen=True, kw_only=True)
class ReplayPassRecord:
    pass_index: int
    pass_id: str
    decision_time: datetime
    outcome: str
    consumed_event_ids: tuple[str, ...]
    activation_state: str
    candidate: Mapping[str, object] | None
    lifecycle_messages: tuple[tuple[str, bool], ...]
    diagnostics: tuple[Mapping[str, object], ...]
    predecessor_digest: str

    def __post_init__(self) -> None:
        if type(self.pass_index) is not int or self.pass_index < 0:
            raise ValueError("pass_index must be a native nonnegative integer")
        _identity(self.pass_id, "pass_id")
        object.__setattr__(self, "decision_time", _utc(self.decision_time, "decision_time"))
        if type(self.outcome) is not str or self.outcome not in _OUTCOMES:
            raise ValueError("outcome must be an explicit replay outcome")
        object.__setattr__(self, "consumed_event_ids", _identity_tuple(self.consumed_event_ids, "consumed_event_ids"))
        if type(self.activation_state) is not str or self.activation_state not in _ACTIVATION_STATES:
            raise ValueError("activation_state must be an explicit activation state")
        if self.candidate is not None:
            if not isinstance(self.candidate, Mapping):
                raise ValueError("candidate must be a JSON object or None")
            candidate = _canonical_value(self.candidate, field="candidate")
            assert isinstance(candidate, Mapping)
            if _contains_forbidden_structured_field(candidate):
                raise ValueError("candidate contains forbidden economic or outcome fields")
            object.__setattr__(self, "candidate", candidate)
        if type(self.lifecycle_messages) is not tuple:
            raise ValueError("lifecycle_messages must be an immutable tuple")
        messages: list[tuple[str, bool]] = []
        for message in self.lifecycle_messages:
            if type(message) is not tuple or len(message) != 2:
                raise ValueError("lifecycle_messages must contain (text, emitted) tuples")
            text, emitted = message
            _identity(text, "lifecycle message")
            if type(emitted) is not bool:
                raise ValueError("lifecycle message emitted must be an explicit bool")
            messages.append((text, emitted))
        object.__setattr__(self, "lifecycle_messages", tuple(messages))
        if type(self.diagnostics) is not tuple:
            raise ValueError("diagnostics must be an immutable tuple")
        diagnostics: list[Mapping[str, object]] = []
        for diagnostic in self.diagnostics:
            if not isinstance(diagnostic, Mapping):
                raise ValueError("diagnostics must contain JSON objects")
            canonical = _canonical_value(diagnostic, field="diagnostics")
            assert isinstance(canonical, Mapping)
            if _contains_forbidden_structured_field(canonical):
                raise ValueError("diagnostics contain forbidden economic or outcome fields")
            diagnostics.append(canonical)
        object.__setattr__(self, "diagnostics", tuple(diagnostics))
        evidence = [item for item in diagnostics if item.get("stage") == _EVIDENCE_DIAGNOSTIC_STAGE]
        if len(evidence) > 1:
            raise ValueError("record cannot contain multiple evidence binding diagnostics")
        commitments: tuple[ReplayEventCommitment, ...] = ()
        baseline_fingerprint: str | None = None
        if evidence:
            metadata = evidence[0]
            if set(metadata) != {"stage", "consumed_event_commitments", "provider_baseline_fingerprint"}:
                raise ValueError("evidence binding diagnostic is not canonical")
            packed = metadata["consumed_event_commitments"]
            if type(packed) is not tuple:
                raise ValueError("evidence commitments must be an immutable tuple")
            try:
                rows = []
                for item in packed:
                    row = dict(item)
                    encoded_time = row.get("available_at")
                    if type(encoded_time) is not str:
                        raise ValueError("commitment available_at must be ISO text")
                    row["available_at"] = datetime.fromisoformat(encoded_time.replace("Z", "+00:00"))
                    rows.append(ReplayEventCommitment(**row))
                commitments = tuple(rows)
            except (TypeError, ValueError) as exc:
                raise ValueError("evidence commitments are invalid") from exc
            if tuple(item.event_id for item in commitments) != self.consumed_event_ids:
                raise ValueError("evidence commitments must match consumed event IDs")
            baseline_fingerprint = metadata["provider_baseline_fingerprint"]
            if type(baseline_fingerprint) is not str or not _SHA256.fullmatch(baseline_fingerprint):
                raise ValueError("provider_baseline_fingerprint must be a SHA-256 digest")
        object.__setattr__(self, "_consumed_event_commitments", commitments)
        object.__setattr__(self, "_provider_baseline_fingerprint", baseline_fingerprint)
        if type(self.predecessor_digest) is not str or not _SHA256.fullmatch(self.predecessor_digest):
            raise ValueError("predecessor_digest must be a SHA-256 digest")

    def as_dict(self) -> dict[str, object]:
        return {
            "pass_index": self.pass_index, "pass_id": self.pass_id,
            "decision_time": self.decision_time.isoformat(), "outcome": self.outcome,
            "consumed_event_ids": list(self.consumed_event_ids),
            "activation_state": self.activation_state,
            "candidate": None if self.candidate is None else _json_value(self.candidate),
            "lifecycle_messages": [list(message) for message in self.lifecycle_messages],
            "diagnostics": [_json_value(diagnostic) for diagnostic in self.diagnostics],
            "predecessor_digest": self.predecessor_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.as_dict())

    @property
    def consumed_event_commitments(self) -> tuple[ReplayEventCommitment, ...]:
        return self._consumed_event_commitments

    @property
    def provider_baseline_fingerprint(self) -> str | None:
        return self._provider_baseline_fingerprint


@dataclass(frozen=True, kw_only=True)
class ReplayRunLedger:
    run_id: str
    records: tuple[ReplayPassRecord, ...]

    def __post_init__(self) -> None:
        _identity(self.run_id, "run_id")
        if type(self.records) is not tuple:
            raise ValueError("records must be an immutable tuple")
        pass_ids: set[str] = set()
        previous_time: datetime | None = None
        predecessor = canonical_digest({"run_id": self.run_id, "records": []})
        for index, record in enumerate(self.records):
            if type(record) is not ReplayPassRecord:
                raise ValueError("records must contain exact ReplayPassRecord objects")
            if record.pass_index != index:
                raise ValueError("records must have contiguous pass indexes")
            if record.pass_id in pass_ids:
                raise ValueError("records cannot contain duplicate pass_id")
            pass_ids.add(record.pass_id)
            if previous_time is not None and record.decision_time < previous_time:
                raise ValueError("records cannot have backward decision_time")
            if record.predecessor_digest != predecessor:
                raise ValueError("record predecessor_digest does not match prior ledger")
            previous_time = record.decision_time
            predecessor = record.digest

    @classmethod
    def empty(cls, run_id: str) -> ReplayRunLedger:
        return cls(run_id=run_id, records=())

    @property
    def digest(self) -> str:
        return canonical_digest({
            "run_id": self.run_id,
            "records": [record.as_dict() for record in self.records],
        })

    @property
    def next_predecessor_digest(self) -> str:
        return self.records[-1].digest if self.records else self.digest

    def append(self, record: ReplayPassRecord) -> ReplayRunLedger:
        if type(record) is not ReplayPassRecord:
            raise ValueError("record must be an exact ReplayPassRecord")
        if record.pass_index != len(self.records):
            raise ValueError("record pass_index is noncontiguous")
        if any(existing.pass_id == record.pass_id for existing in self.records):
            raise ValueError("record has duplicate pass_id")
        if self.records and record.decision_time < self.records[-1].decision_time:
            raise ValueError("record has backward decision_time")
        if record.predecessor_digest != self.next_predecessor_digest:
            raise ValueError("record predecessor_digest does not match ledger")
        return ReplayRunLedger(run_id=self.run_id, records=self.records + (record,))

    def as_dict(self) -> dict[str, object]:
        return {"run_id": self.run_id, "records": [record.as_dict() for record in self.records]}

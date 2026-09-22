"""Private supplied-evidence contracts for full-tree causal observation.

The public manifest contains commitments only.  Raw frames, text, bytes and
other supplied artifact values deliberately remain private to the bundle.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from math import isfinite
import re
from types import MappingProxyType
from typing import Any

import pandas as pd

from ._vendor.correction import Correction
from .bars import _utc


_ARTIFACT_KINDS = frozenset({
    "FRAME", "CLOCK", "TEXT", "REPORT_LIST", "BYTES", "SHADOW_RESULT", "ERROR",
})
_OPERATION_KINDS = frozenset({
    "FETCH_CORRECTED", "NOW_UTC", "NOW_EPOCH", "NOW_TIMESTAMP",
    "CALENDAR_TEXT", "CALENDAR_EXISTS", "LIST_REPORTS", "READ_REPORT", "READ_TV_CSV",
    "DEEP_EXISTS", "DEEP_BYTES", "ENSURE_SHADOW_PARENT", "SHADOW_OPEN",
})
_VARIANTS = frozenset({"full_tree:house", "full_tree:strict"})
_PASS_MODES = frozenset({"TREE_WALK", "TREE_REVALIDATION"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OPERATION_ARTIFACT_KINDS = {
    "FETCH_CORRECTED": frozenset({"FRAME", "ERROR"}),
    "NOW_UTC": frozenset({"CLOCK", "ERROR"}),
    "NOW_EPOCH": frozenset({"CLOCK", "ERROR"}),
    "NOW_TIMESTAMP": frozenset({"CLOCK", "ERROR"}),
    "CALENDAR_TEXT": frozenset({"TEXT", "ERROR"}),
    "CALENDAR_EXISTS": frozenset({"SHADOW_RESULT", "ERROR"}),
    "LIST_REPORTS": frozenset({"REPORT_LIST", "ERROR"}),
    "READ_REPORT": frozenset({"TEXT", "ERROR"}),
    "READ_TV_CSV": frozenset({"TEXT", "ERROR"}),
    "DEEP_EXISTS": frozenset({"SHADOW_RESULT", "ERROR"}),
    "DEEP_BYTES": frozenset({"BYTES", "ERROR"}),
    "ENSURE_SHADOW_PARENT": frozenset({"SHADOW_RESULT", "ERROR"}),
    "SHADOW_OPEN": frozenset({"SHADOW_RESULT", "ERROR"}),
}


def _identity(value: object, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a nonempty trimmed string")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"{field_name} must be UTF-8 encodable") from exc
    return value


def _sha256(value: object, field_name: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"FULL_TREE_INVALID_{field_name}_DIGEST")
    return value


def _canonical_value(value: object, *, field_name: str) -> object:
    if value is None or type(value) is bool:
        return value
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"{field_name} must contain UTF-8 text") from exc
        return value
    if type(value) in (int, float):
        if not isfinite(float(value)):
            raise ValueError(f"{field_name} must contain finite JSON numbers")
        return value
    if type(value) in (list, tuple):
        return tuple(_canonical_value(item, field_name=field_name) for item in value)
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key in sorted(value):
            if type(key) is not str:
                raise ValueError(f"{field_name} must contain string JSON keys")
            result[key] = _canonical_value(value[key], field_name=field_name)
        return MappingProxyType(result)
    raise ValueError(f"{field_name} must contain finite JSON-compatible values")


def _public_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _public_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_public_json(item) for item in value]
    return value


def canonical_operation_arguments(arguments: Mapping[str, object]) -> Mapping[str, object]:
    """Detach finite JSON arguments in a stable mapping order."""
    if not isinstance(arguments, Mapping):
        raise ValueError("FULL_TREE_OPERATION_ARGUMENTS must be a JSON object")
    result = _canonical_value(arguments, field_name="FULL_TREE_OPERATION_ARGUMENTS")
    assert isinstance(result, Mapping)
    return result


def _manifest_digest(manifest: Mapping[str, object]) -> str:
    encoded = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def pending_plan_digest(pending_plan: Mapping[str, object]) -> str:
    """Commit a private pending plan without placing it in public output."""
    canonical = canonical_operation_arguments(pending_plan)
    return _manifest_digest({"pending_plan": _public_json(canonical)})


def _artifact_value(kind: str, value: object) -> object:
    """Validate a raw artifact without serializing or otherwise exposing it."""
    if kind == "FRAME":
        valid = isinstance(value, TreeFramePayload)
    elif kind == "CLOCK":
        valid = isinstance(value, datetime) or (type(value) in (int, float) and isfinite(float(value)))
        if isinstance(value, datetime):
            value = _utc(value, "clock value")
    elif kind == "TEXT":
        valid = type(value) is str
    elif kind == "REPORT_LIST":
        valid = type(value) in (list, tuple) and all(type(item) is str for item in value)
    elif kind == "BYTES":
        valid = type(value) is bytes
    elif kind == "SHADOW_RESULT":
        valid = value is None or type(value) is bool
    else:
        assert kind == "ERROR"
        valid = isinstance(value, ProviderErrorPayload)
    if not valid:
        raise ValueError("FULL_TREE_ARTIFACT_VALUE_KIND")
    return value


@dataclass(frozen=True, kw_only=True)
class TreeFramePayload:
    """Private raw tree frame and its exact source correction."""

    frame: pd.DataFrame
    correction: Correction | None

    def __post_init__(self) -> None:
        if not isinstance(self.frame, pd.DataFrame):
            raise ValueError("frame must be a pandas DataFrame")
        if self.correction is not None and not isinstance(self.correction, Correction):
            raise ValueError("correction must be a Correction or None")


@dataclass(frozen=True, kw_only=True)
class ProviderErrorPayload:
    """Private declared error raised exactly when its operation is consumed."""

    error_type: type[Exception]
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.error_type, type) or not issubclass(self.error_type, Exception):
            raise ValueError("error_type must be an exception class")
        _identity(self.message, "message")


@dataclass(frozen=True, kw_only=True)
class FullTreeArtifact:
    artifact_id: str
    kind: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    content_digest: str
    value: object = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        _identity(self.artifact_id, "artifact_id")
        if type(self.kind) is not str or self.kind not in _ARTIFACT_KINDS:
            raise ValueError("FULL_TREE_UNKNOWN_ARTIFACT_KIND")
        for name in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if not self.observed_at <= self.available_at <= self.covered_through:
            raise ValueError("FULL_TREE_INVALID_ARTIFACT_WINDOW")
        _sha256(self.content_digest, "ARTIFACT")
        object.__setattr__(self, "value", _artifact_value(self.kind, self.value))

    def commitment(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "covered_through": self.covered_through.isoformat(),
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, kw_only=True)
class FullTreeOperation:
    operation_id: str
    kind: str
    arguments: Mapping[str, object]
    artifact_id: str
    sequence: int

    def __post_init__(self) -> None:
        _identity(self.operation_id, "operation_id")
        _identity(self.artifact_id, "artifact_id")
        if type(self.kind) is not str or self.kind not in _OPERATION_KINDS:
            raise ValueError("FULL_TREE_UNKNOWN_OPERATION_KIND")
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("FULL_TREE_OPERATION_SEQUENCE")
        object.__setattr__(self, "arguments", canonical_operation_arguments(self.arguments))

    def commitment(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "kind": self.kind,
            "arguments": _public_json(self.arguments),
            "artifact_id": self.artifact_id,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, kw_only=True)
class FullTreePass:
    pass_id: str
    decision_time: datetime
    source_variant: str
    mode: str
    operations: tuple[FullTreeOperation, ...]
    pending_plan: Mapping[str, object] | None = field(default=None, repr=False, compare=False, hash=False)
    pending_plan_digest: str | None = None

    def __post_init__(self) -> None:
        _identity(self.pass_id, "pass_id")
        object.__setattr__(self, "decision_time", _utc(self.decision_time, "decision_time"))
        if type(self.source_variant) is not str or self.source_variant not in _VARIANTS:
            raise ValueError("FULL_TREE_UNSUPPORTED_VARIANT")
        if type(self.mode) is not str or self.mode not in _PASS_MODES:
            raise ValueError("FULL_TREE_UNSUPPORTED_PASS_MODE")
        if self.mode == "TREE_WALK":
            if self.pending_plan is not None or self.pending_plan_digest is not None:
                raise ValueError("FULL_TREE_PENDING_PLAN_FOR_WALK")
        else:
            if not isinstance(self.pending_plan, Mapping) or type(self.pending_plan_digest) is not str:
                raise ValueError("FULL_TREE_PENDING_PLAN")
            private_plan = canonical_operation_arguments(self.pending_plan)
            expected_pending_digest = pending_plan_digest(private_plan)
            if self.pending_plan_digest != expected_pending_digest:
                raise ValueError("FULL_TREE_PENDING_PLAN_DIGEST")
            object.__setattr__(self, "pending_plan", private_plan)
        if type(self.operations) is not tuple:
            raise ValueError("operations must be an immutable tuple")
        operation_ids: set[str] = set()
        for expected_sequence, operation in enumerate(self.operations):
            if type(operation) is not FullTreeOperation:
                raise ValueError("operations must contain exact FullTreeOperation objects")
            if operation.operation_id in operation_ids:
                raise ValueError("FULL_TREE_DUPLICATE_OPERATION_ID")
            if operation.sequence != expected_sequence:
                raise ValueError("FULL_TREE_OPERATION_SEQUENCE")
            operation_ids.add(operation.operation_id)

    def commitment(self) -> dict[str, object]:
        return {
            "pass_id": self.pass_id,
            "decision_time": self.decision_time.isoformat(),
            "source_variant": self.source_variant,
            "mode": self.mode,
            "pending_plan_digest": self.pending_plan_digest,
            "operations": [operation.commitment() for operation in self.operations],
        }


@dataclass(frozen=True, kw_only=True)
class FullTreeEvidenceBundle:
    run_id: str
    instrument: str
    artifacts: tuple[FullTreeArtifact, ...]
    passes: tuple[FullTreePass, ...]

    def __post_init__(self) -> None:
        _identity(self.run_id, "run_id")
        instrument = _identity(self.instrument, "instrument")
        if instrument.count(":") != 1 or not all(instrument.split(":")) or any(char.isspace() for char in instrument):
            raise ValueError("instrument must be an exact non-whitespace venue:symbol")
        if type(self.artifacts) is not tuple or type(self.passes) is not tuple:
            raise ValueError("artifacts and passes must be immutable tuples")
        artifact_by_id: dict[str, FullTreeArtifact] = {}
        for artifact in self.artifacts:
            if type(artifact) is not FullTreeArtifact:
                raise ValueError("artifacts must contain exact FullTreeArtifact objects")
            if artifact.artifact_id in artifact_by_id:
                raise ValueError("FULL_TREE_DUPLICATE_ARTIFACT_ID")
            artifact_by_id[artifact.artifact_id] = artifact
        pass_ids: set[str] = set()
        previous_time: datetime | None = None
        for replay_pass in self.passes:
            if type(replay_pass) is not FullTreePass:
                raise ValueError("passes must contain exact FullTreePass objects")
            if replay_pass.pass_id in pass_ids:
                raise ValueError("FULL_TREE_DUPLICATE_PASS_ID")
            if previous_time is not None and replay_pass.decision_time <= previous_time:
                raise ValueError("FULL_TREE_PASS_TIME_ORDER")
            for operation in replay_pass.operations:
                artifact = artifact_by_id.get(operation.artifact_id)
                if artifact is None:
                    raise ValueError("FULL_TREE_UNKNOWN_OPERATION_ARTIFACT")
                if artifact.kind not in _OPERATION_ARTIFACT_KINDS[operation.kind]:
                    raise ValueError("FULL_TREE_OPERATION_ARTIFACT_KIND")
                if not artifact.available_at <= replay_pass.decision_time <= artifact.covered_through:
                    raise ValueError("FULL_TREE_ARTIFACT_UNAVAILABLE_FOR_PASS")
            pass_ids.add(replay_pass.pass_id)
            previous_time = replay_pass.decision_time

    def artifact_by_id(self, artifact_id: str) -> FullTreeArtifact:
        _identity(artifact_id, "artifact_id")
        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise KeyError(artifact_id)

    def pass_by_id(self, pass_id: str) -> FullTreePass:
        _identity(pass_id, "pass_id")
        for replay_pass in self.passes:
            if replay_pass.pass_id == pass_id:
                return replay_pass
        raise KeyError(pass_id)

    def as_dict(self) -> dict[str, object]:
        return full_tree_manifest(self)


def full_tree_manifest(bundle: FullTreeEvidenceBundle) -> dict[str, object]:
    """Return the public commitment surface; no artifact value is serialized."""
    if type(bundle) is not FullTreeEvidenceBundle:
        raise ValueError("bundle must be an exact FullTreeEvidenceBundle")
    return {
        "schema_version": "full-tree-evidence-manifest-v1",
        "run_id": bundle.run_id,
        "instrument": bundle.instrument,
        "artifacts": [artifact.commitment() for artifact in bundle.artifacts],
        "passes": [replay_pass.commitment() for replay_pass in bundle.passes],
    }


def full_tree_manifest_digest(bundle: FullTreeEvidenceBundle) -> str:
    """Return the SHA-256 public commitment for a private evidence bundle."""
    return _manifest_digest(full_tree_manifest(bundle))

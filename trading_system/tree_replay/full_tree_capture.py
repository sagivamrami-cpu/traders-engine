"""Record caller-supplied full-tree source calls into private evidence bundles.

This module deliberately owns no data loader.  A caller supplies every raw
response, its availability window and a digest from an approved upstream
adapter.  The recorder turns each actual port call into a distinct scheduled
artifact; later work invokes the source tree through this recorder.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
from io import StringIO
import json
from types import MappingProxyType
from typing import Protocol

import pandas as pd

from .bars import _utc
from .full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    ProviderErrorPayload,
    TreeFramePayload,
    canonical_operation_arguments,
    full_tree_manifest_digest,
)


class FullTreeCaptureError(ValueError):
    """A supplied historical value cannot be captured faithfully."""


@dataclass(frozen=True, kw_only=True)
class CapturedValue:
    """One private historical response provided by an upstream adapter."""

    value: object
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    content_digest: str

    def __post_init__(self) -> None:
        for name in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if not self.observed_at <= self.available_at <= self.covered_through:
            raise ValueError("FULL_TREE_CAPTURE_VALUE_WINDOW")


class FullTreeCaptureInput(Protocol):
    """Caller-owned data boundary; implementations must perform no implicit fallback."""

    def read(
        self, kind: str, arguments: Mapping[str, object], *, decision_time: datetime,
    ) -> CapturedValue: ...


@dataclass(frozen=True, kw_only=True)
class FullTreeCaptureReceipt:
    """Payload-free commitment to a single captured evidence pass."""

    bundle_manifest_digest: str
    pass_id: str
    operation_count: int
    trace_digest: str


@dataclass(frozen=True, kw_only=True)
class FullTreeCaptureResult:
    """Private bundle plus a public-safe receipt; never a source result."""

    bundle: FullTreeEvidenceBundle
    receipt: FullTreeCaptureReceipt


_ARTIFACT_KIND = {
    "FETCH_CORRECTED": "FRAME",
    "NOW_UTC": "CLOCK",
    "NOW_EPOCH": "CLOCK",
    "NOW_TIMESTAMP": "CLOCK",
    "CALENDAR_TEXT": "TEXT",
    "CALENDAR_EXISTS": "SHADOW_RESULT",
    "LIST_REPORTS": "REPORT_LIST",
    "READ_REPORT": "TEXT",
    "READ_TV_CSV": "TEXT",
    "DEEP_EXISTS": "SHADOW_RESULT",
    "DEEP_BYTES": "BYTES",
    "ENSURE_SHADOW_PARENT": "SHADOW_RESULT",
    "SHADOW_OPEN": "SHADOW_RESULT",
}


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _copied_value(value: object) -> object:
    if isinstance(value, TreeFramePayload):
        return TreeFramePayload(frame=value.frame.copy(deep=True), correction=value.correction)
    if type(value) in (list, tuple):
        return tuple(value)
    return value


class _CaptureShadowBuffer:
    """Capture-source equivalent of an in-memory source shadow file."""

    def __init__(self, source: "FullTreeRecordingSource", trace_index: int) -> None:
        self._source = source
        self._trace_index = trace_index
        self._buffer = StringIO()

    def __enter__(self) -> StringIO:
        return self._buffer

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        text = self._buffer.getvalue()
        self._buffer.close()
        entry = dict(self._source._trace[self._trace_index])
        entry["shadow_write_digest"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entry["shadow_write_bytes"] = len(text.encode("utf-8"))
        self._source._trace[self._trace_index] = MappingProxyType(entry)
        return False


class FullTreeRecordingSource:
    """The full-tree raw-port surface backed only by ``FullTreeCaptureInput``."""

    def __init__(self, capture: "FullTreeEvidenceCapture") -> None:
        self._capture = capture
        self._trace: list[Mapping[str, object]] = []

    def _read(self, kind: str, arguments: Mapping[str, object]) -> object:
        canonical = canonical_operation_arguments(arguments)
        try:
            supplied = self._capture._input.read(
                kind, canonical, decision_time=self._capture.decision_time,
            )
        except FullTreeCaptureError:
            raise
        except Exception as exc:
            raise FullTreeCaptureError("FULL_TREE_CAPTURE_INPUT") from exc
        if type(supplied) is not CapturedValue:
            raise FullTreeCaptureError("FULL_TREE_CAPTURE_VALUE")
        if not supplied.available_at <= self._capture.decision_time <= supplied.covered_through:
            raise FullTreeCaptureError("FULL_TREE_CAPTURE_UNAVAILABLE")
        artifact_kind = "ERROR" if isinstance(supplied.value, ProviderErrorPayload) else _ARTIFACT_KIND[kind]
        sequence = len(self._capture._operations)
        artifact_id = f"{self._capture.pass_id}:artifact:{sequence}"
        operation_id = f"{self._capture.pass_id}:operation:{sequence}"
        try:
            artifact = FullTreeArtifact(
                artifact_id=artifact_id,
                kind=artifact_kind,
                observed_at=supplied.observed_at,
                available_at=supplied.available_at,
                covered_through=supplied.covered_through,
                content_digest=supplied.content_digest,
                value=_copied_value(supplied.value),
            )
            operation = FullTreeOperation(
                operation_id=operation_id,
                kind=kind,
                arguments=canonical,
                artifact_id=artifact_id,
                sequence=sequence,
            )
        except ValueError as exc:
            raise FullTreeCaptureError("FULL_TREE_CAPTURE_VALUE") from exc
        self._capture._artifacts.append(artifact)
        self._capture._operations.append(operation)
        self._trace.append(MappingProxyType({
            "operation_id": operation.operation_id,
            "kind": operation.kind,
            "arguments": dict(operation.arguments),
            "artifact_id": artifact.artifact_id,
            "content_digest": artifact.content_digest,
        }))
        if artifact.kind == "ERROR":
            payload = artifact.value
            assert isinstance(payload, ProviderErrorPayload)
            raise payload.error_type(payload.message)
        return artifact.value

    def fetch_corrected(self, symbol: str, timeframe: str, lookback: int):
        payload = self._read("FETCH_CORRECTED", {
            "symbol": symbol, "timeframe": timeframe, "lookback": lookback,
        })
        assert isinstance(payload, TreeFramePayload)
        return payload.frame.copy(deep=True), payload.correction

    def now_utc(self) -> datetime:
        value = self._read("NOW_UTC", {})
        assert isinstance(value, datetime)
        return value

    def now_epoch(self) -> float:
        value = self._read("NOW_EPOCH", {})
        if isinstance(value, datetime):
            return value.timestamp()
        assert type(value) in (int, float)
        return float(value)

    def now_timestamp(self, *, tz):
        value = self._read("NOW_TIMESTAMP", {"tz": str(tz)})
        instant = pd.Timestamp(value) if isinstance(value, datetime) else pd.Timestamp(value, unit="s", tz="UTC")
        return instant.tz_convert(tz)

    def calendar_text(self, path: str) -> str:
        return self._read("CALENDAR_TEXT", {"path": path})

    def calendar_exists(self, path: str) -> bool:
        return self._read("CALENDAR_EXISTS", {"path": path})

    def list_reports(self) -> list[str]:
        return list(self._read("LIST_REPORTS", {}))

    def read_report(self, logical_id: str) -> str:
        return self._read("READ_REPORT", {"logical_id": logical_id})

    def read_tv_csv(self, filename: str) -> str:
        return self._read("READ_TV_CSV", {"filename": filename})

    def deep_exists(self, key: str) -> bool:
        return self._read("DEEP_EXISTS", {"key": key})

    def deep_bytes(self, key: str) -> bytes:
        return self._read("DEEP_BYTES", {"key": key})

    def ensure_shadow_parent(self, *, parents: bool, exist_ok: bool):
        return self._read("ENSURE_SHADOW_PARENT", {"parents": parents, "exist_ok": exist_ok})

    def shadow_open(self, mode: str, encoding: str) -> _CaptureShadowBuffer:
        self._read("SHADOW_OPEN", {"mode": mode, "encoding": encoding})
        return _CaptureShadowBuffer(self, len(self._trace) - 1)

    def public_trace(self) -> tuple[Mapping[str, object], ...]:
        return tuple(MappingProxyType(dict(item)) for item in self._trace)


class FullTreeEvidenceCapture:
    """Collect one supplied full-tree pass; source execution is added separately."""

    def __init__(
        self, source_input: FullTreeCaptureInput, *, run_id: str, instrument: str,
        pass_id: str, decision_time: datetime, source_variant: str,
    ) -> None:
        self._input = source_input
        self.run_id = run_id
        self.instrument = instrument
        self.pass_id = pass_id
        self.decision_time = _utc(decision_time, "decision_time")
        self.source_variant = source_variant
        self._artifacts: list[FullTreeArtifact] = []
        self._operations: list[FullTreeOperation] = []
        self.source = FullTreeRecordingSource(self)

    def finish(self) -> FullTreeCaptureResult:
        bundle = FullTreeEvidenceBundle(
            run_id=self.run_id,
            instrument=self.instrument,
            artifacts=tuple(self._artifacts),
            passes=(FullTreePass(
                pass_id=self.pass_id,
                decision_time=self.decision_time,
                source_variant=self.source_variant,
                mode="TREE_WALK",
                operations=tuple(self._operations),
            ),),
        )
        trace = [dict(item) for item in self.source.public_trace()]
        return FullTreeCaptureResult(
            bundle=bundle,
            receipt=FullTreeCaptureReceipt(
                bundle_manifest_digest=full_tree_manifest_digest(bundle),
                pass_id=self.pass_id,
                operation_count=len(self._operations),
                trace_digest=_digest(trace),
            ),
        )

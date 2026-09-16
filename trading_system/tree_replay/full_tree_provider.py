"""Ordered in-memory raw-port provider for complete-tree causal replay."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import hashlib
from io import StringIO
from types import MappingProxyType

import pandas as pd

from .full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    ProviderErrorPayload,
    TreeFramePayload,
    canonical_operation_arguments,
)


class FullTreeProviderError(ValueError):
    """A supplied full-tree operation cannot be reproduced faithfully."""


class _ShadowBuffer:
    """In-memory shadow sink that commits a write without exposing its text."""

    def __init__(self, provider: "FullTreeCausalProvider", trace_index: int) -> None:
        self._provider = provider
        self._trace_index = trace_index
        self._buffer = StringIO()

    def __enter__(self) -> StringIO:
        return self._buffer

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        text = self._buffer.getvalue()
        self._buffer.close()
        entry = dict(self._provider._trace[self._trace_index])
        entry["shadow_write_digest"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entry["shadow_write_bytes"] = len(text.encode("utf-8"))
        self._provider._trace[self._trace_index] = MappingProxyType(entry)
        return False


class FullTreeCausalProvider:
    """Expose only scheduled raw calls for one immutable full-tree pass."""

    def __init__(self, bundle: FullTreeEvidenceBundle, pass_id: str) -> None:
        if type(bundle) is not FullTreeEvidenceBundle:
            raise ValueError("bundle must be an exact FullTreeEvidenceBundle")
        self._bundle = bundle
        self._pass = bundle.pass_by_id(pass_id)
        self._artifacts = {artifact.artifact_id: artifact for artifact in bundle.artifacts}
        self._cursor = 0
        self._trace: list[Mapping[str, object]] = []

    @property
    def decision_time(self):
        return self._pass.decision_time

    def _next_operation(self) -> FullTreeOperation:
        if self._cursor >= len(self._pass.operations):
            raise FullTreeProviderError("FULL_TREE_UNSCHEDULED_OPERATION")
        return self._pass.operations[self._cursor]

    def _consume(self, kind: str, arguments: Mapping[str, object]) -> FullTreeArtifact:
        expected = self._next_operation()
        actual_arguments = canonical_operation_arguments(arguments)
        if expected.kind != kind or expected.arguments != actual_arguments:
            raise FullTreeProviderError("FULL_TREE_OPERATION_MISMATCH")
        artifact = self._artifacts[expected.artifact_id]
        if not artifact.available_at <= self.decision_time <= artifact.covered_through:
            raise FullTreeProviderError("FULL_TREE_ARTIFACT_UNAVAILABLE")
        self._cursor += 1
        self._trace.append(MappingProxyType({
            "operation_id": expected.operation_id,
            "kind": expected.kind,
            "arguments": dict(expected.arguments),
            "artifact_id": artifact.artifact_id,
            "content_digest": artifact.content_digest,
        }))
        if artifact.kind == "ERROR":
            payload = artifact.value
            assert isinstance(payload, ProviderErrorPayload)
            raise payload.error_type(payload.message)
        return artifact

    def fetch_corrected(self, symbol: str, timeframe: str, lookback: int):
        artifact = self._consume("FETCH_CORRECTED", {
            "symbol": symbol, "timeframe": timeframe, "lookback": lookback,
        })
        payload = artifact.value
        assert isinstance(payload, TreeFramePayload)
        return payload.frame.copy(deep=True), payload.correction

    def now_utc(self) -> datetime:
        artifact = self._consume("NOW_UTC", {})
        value = artifact.value
        if not isinstance(value, datetime):
            raise FullTreeProviderError("FULL_TREE_CLOCK_VALUE")
        return value

    def now_epoch(self) -> float:
        artifact = self._consume("NOW_EPOCH", {})
        value = artifact.value
        if isinstance(value, datetime):
            return value.timestamp()
        if type(value) in (int, float):
            return float(value)
        raise FullTreeProviderError("FULL_TREE_CLOCK_VALUE")

    def now_timestamp(self, *, tz):
        artifact = self._consume("NOW_TIMESTAMP", {"tz": str(tz)})
        value = artifact.value
        if isinstance(value, datetime):
            instant = pd.Timestamp(value)
        elif type(value) in (int, float):
            instant = pd.Timestamp(value, unit="s", tz="UTC")
        else:
            raise FullTreeProviderError("FULL_TREE_CLOCK_VALUE")
        return instant.tz_convert(tz)

    def calendar_text(self, path: str) -> str:
        artifact = self._consume("CALENDAR_TEXT", {"path": path})
        value = artifact.value
        assert type(value) is str
        return value

    def calendar_exists(self, path: str) -> bool:
        artifact = self._consume("CALENDAR_EXISTS", {"path": path})
        if type(artifact.value) is not bool:
            raise FullTreeProviderError("FULL_TREE_BOOLEAN_VALUE")
        return artifact.value

    def list_reports(self) -> list[str]:
        artifact = self._consume("LIST_REPORTS", {})
        value = artifact.value
        assert type(value) in (list, tuple)
        return list(value)

    def read_report(self, logical_id: str) -> str:
        artifact = self._consume("READ_REPORT", {"logical_id": logical_id})
        value = artifact.value
        assert type(value) is str
        return value

    def read_tv_csv(self, filename: str) -> str:
        artifact = self._consume("READ_TV_CSV", {"filename": filename})
        value = artifact.value
        assert type(value) is str
        return value

    def deep_exists(self, key: str) -> bool:
        artifact = self._consume("DEEP_EXISTS", {"key": key})
        if type(artifact.value) is not bool:
            raise FullTreeProviderError("FULL_TREE_BOOLEAN_VALUE")
        return artifact.value

    def deep_bytes(self, key: str) -> bytes:
        artifact = self._consume("DEEP_BYTES", {"key": key})
        value = artifact.value
        assert type(value) is bytes
        return value

    def ensure_shadow_parent(self, *, parents: bool, exist_ok: bool):
        artifact = self._consume("ENSURE_SHADOW_PARENT", {
            "parents": parents, "exist_ok": exist_ok,
        })
        if artifact.value is not None:
            raise FullTreeProviderError("FULL_TREE_SHADOW_PARENT_VALUE")
        return None

    def shadow_open(self, mode: str, encoding: str) -> _ShadowBuffer:
        artifact = self._consume("SHADOW_OPEN", {"mode": mode, "encoding": encoding})
        if artifact.value is not None:
            raise FullTreeProviderError("FULL_TREE_SHADOW_OPEN_VALUE")
        return _ShadowBuffer(self, len(self._trace) - 1)

    def public_trace(self) -> tuple[Mapping[str, object], ...]:
        return tuple(MappingProxyType(dict(item)) for item in self._trace)

    def assert_no_unexpected_calls(self) -> None:
        if self._cursor != len(self._pass.operations):
            raise FullTreeProviderError("FULL_TREE_UNCONSUMED_OPERATIONS")

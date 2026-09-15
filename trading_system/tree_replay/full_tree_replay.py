"""Offline observation runner for the accepted complete decision tree."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from ._vendor.tree_walk import TreeReader
from .full_tree_contracts import FullTreeEvidenceBundle
from .full_tree_provider import FullTreeCausalProvider, FullTreeProviderError
from .tree_revalidation import TreeRevalidation


_OUTCOMES = frozenset({
    "TREE_BLOCKED", "TREE_STOPPED", "TREE_OBSERVED_NO_PLAN", "TREE_REFUSED_PLAN",
    "TREE_CANDIDATE_OBSERVED", "UNSUPPORTED",
})
_ROOT_DIGEST = "0" * 64


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_reason_digest(reason: object) -> str | None:
    return None if reason is None else _digest({"source_reason": str(reason)})


def _walk_digest(walk: object) -> str:
    return _digest({
        "complete": bool(getattr(walk, "complete", False)),
        "direction": getattr(walk, "direction", None),
        "reached": getattr(walk, "reached", None),
        "passed": list(getattr(walk, "passed", ())),
        "stopped": _source_reason_digest(getattr(walk, "stopped_because", None)),
        "refused": getattr(walk, "refused", None) is not None,
    })


def _plan_digest(plan: object | None) -> str | None:
    if plan is None:
        return None
    targets = getattr(plan, "targets", ())
    return _digest({
        "symbol": getattr(plan, "symbol", None),
        "close": getattr(plan, "close", None),
        "kind": getattr(plan, "kind", None),
        "direction": getattr(plan, "direction", None),
        "entry": getattr(plan, "entry", None),
        "stop": getattr(plan, "stop", None),
        "targets": [list(target) for target in targets],
        "atr": getattr(plan, "atr", None),
        "style": getattr(plan, "style", None),
        "refusal": _source_reason_digest(getattr(plan, "refusal", None)),
    })


def observation_record_payload(record: "FullTreeObservationRecord") -> dict[str, object]:
    """Return the raw-payload-free fields protected by ``record_digest``."""
    return {
        "pass_id": record.pass_id,
        "decision_time": record.decision_time,
        "source_variant": record.source_variant,
        "outcome": record.outcome,
        "reached_stage": record.reached_stage,
        "direction": record.direction,
        "reason_category": record.reason_category,
        "source_reason_digest": record.source_reason_digest,
        "walk_digest": record.walk_digest,
        "plan_digest": record.plan_digest,
        "trace_digest": record.trace_digest,
        "unreached_operation_ids": record.unreached_operation_ids,
        "previous_record_digest": record.previous_record_digest,
        "revalidation_ok": record.revalidation_ok,
        "revalidation_verified": record.revalidation_verified,
    }


@dataclass(frozen=True, kw_only=True)
class FullTreeObservationRecord:
    pass_id: str
    decision_time: str
    source_variant: str
    outcome: str
    reached_stage: str | None
    direction: str | None
    reason_category: str | None
    source_reason_digest: str | None
    walk_digest: str | None
    plan_digest: str | None
    trace_digest: str
    unreached_operation_ids: tuple[str, ...]
    previous_record_digest: str
    record_digest: str
    revalidation_ok: bool | None = None
    revalidation_verified: bool | None = None


@dataclass(frozen=True, kw_only=True)
class FullTreeReplayResult:
    record: FullTreeObservationRecord


class FullTreeCausalReplay:
    """Run one full-tree pass from a caller-retained evidence bundle."""

    def __init__(self, bundle: FullTreeEvidenceBundle) -> None:
        if type(bundle) is not FullTreeEvidenceBundle:
            raise ValueError("bundle must be an exact FullTreeEvidenceBundle")
        self._bundle = bundle
        self._records: list[FullTreeObservationRecord] = []

    @property
    def records(self) -> tuple[FullTreeObservationRecord, ...]:
        return tuple(self._records)

    def run_all(self) -> "FullTreeCausalReplay":
        while len(self._records) < len(self._bundle.passes):
            self.run_pass(self._bundle.passes[len(self._records)].pass_id)
        return self

    def checkpoint_after(self, result: FullTreeReplayResult, *, next_pass_index: int):
        from .full_tree_checkpoint import FullTreeProviderBaseline, FullTreeReplayCheckpoint

        if type(result) is not FullTreeReplayResult or not self._records or result.record != self._records[-1]:
            raise ValueError("FULL_TREE_CHECKPOINT_RESULT")
        if type(next_pass_index) is not int or next_pass_index != len(self._records):
            raise ValueError("FULL_TREE_CHECKPOINT_INDEX")
        baseline = FullTreeProviderBaseline.capture(self._bundle)
        return FullTreeReplayCheckpoint(
            baseline_digest=baseline.baseline_digest,
            bundle_manifest_digest=baseline.bundle_manifest_digest,
            records=tuple(self._records),
            next_pass_index=next_pass_index,
            last_completed_decision_time=self._records[-1].decision_time,
        )

    @classmethod
    def resume(cls, bundle: FullTreeEvidenceBundle, checkpoint) -> "FullTreeCausalReplay":
        from .full_tree_checkpoint import FullTreeProviderBaseline, FullTreeReplayCheckpoint

        if type(checkpoint) is not FullTreeReplayCheckpoint:
            raise ValueError("FULL_TREE_CHECKPOINT_TYPE")
        baseline = FullTreeProviderBaseline.capture(bundle)
        if (
            checkpoint.bundle_manifest_digest != baseline.bundle_manifest_digest
            or checkpoint.baseline_digest != baseline.baseline_digest
        ):
            raise ValueError("FULL_TREE_CHECKPOINT_BUNDLE_MISMATCH")
        if type(checkpoint.next_pass_index) is not int or checkpoint.next_pass_index != len(checkpoint.records):
            raise ValueError("FULL_TREE_CHECKPOINT_INDEX")
        if checkpoint.next_pass_index > len(bundle.passes):
            raise ValueError("FULL_TREE_CHECKPOINT_INDEX")
        replay = cls(bundle)
        previous = _ROOT_DIGEST
        for index, record in enumerate(checkpoint.records):
            if type(record) is not FullTreeObservationRecord:
                raise ValueError("FULL_TREE_CHECKPOINT_RECORD")
            expected_pass = bundle.passes[index]
            if record.pass_id != expected_pass.pass_id or record.decision_time != expected_pass.decision_time.isoformat():
                raise ValueError("FULL_TREE_CHECKPOINT_RECORD")
            if record.previous_record_digest != previous or record.record_digest != _digest(observation_record_payload(record)):
                raise ValueError("FULL_TREE_CHECKPOINT_RECORD")
            previous = record.record_digest
            replay._records.append(record)
        expected_time = replay._records[-1].decision_time if replay._records else None
        if checkpoint.last_completed_decision_time != expected_time:
            raise ValueError("FULL_TREE_CHECKPOINT_RECORD")
        return replay

    def run_pass(self, pass_id: str) -> FullTreeReplayResult:
        selected = self._bundle.pass_by_id(pass_id)
        if len(self._records) >= len(self._bundle.passes):
            raise ValueError("FULL_TREE_PASS_ORDER")
        expected = self._bundle.passes[len(self._records)]
        if selected.pass_id != expected.pass_id:
            raise ValueError("FULL_TREE_PASS_ORDER")
        provider = FullTreeCausalProvider(self._bundle, pass_id)
        if selected.mode == "TREE_REVALIDATION":
            return self._run_revalidation(selected, provider)
        if selected.mode != "TREE_WALK":
            raise ValueError("FULL_TREE_PASS_MODE_MISMATCH")
        try:
            reader = TreeReader(provider)
            walk = reader.walk(
                self._bundle.instrument,
                selected.source_variant.removeprefix("full_tree:"),
            )
            plan = reader.trade_from_walk(walk) if walk.complete and walk.direction else None
            outcome, reason_category, reason = self._classify(walk, plan)
            walk_digest = _walk_digest(walk)
            plan_digest = _plan_digest(plan if plan is not None else getattr(walk, "refused", None))
            reached_stage = getattr(walk, "reached", None)
            direction = getattr(walk, "direction", None)
        except FullTreeProviderError as exc:
            outcome, reason_category, reason = "TREE_BLOCKED", "PROVIDER_CONTRACT", str(exc)
            walk_digest = plan_digest = reached_stage = direction = None
        return self._append_record(
            selected=selected,
            provider=provider,
            outcome=outcome,
            reason_category=reason_category,
            reason=reason,
            walk_digest=walk_digest,
            plan_digest=plan_digest,
            reached_stage=reached_stage,
            direction=direction,
        )

    def _run_revalidation(self, selected, provider: FullTreeCausalProvider) -> FullTreeReplayResult:
        assert selected.pending_plan is not None
        try:
            pending = dict(selected.pending_plan)
            ok, reason, verified = TreeRevalidation(provider).revalidate_pending(pending)
            if type(ok) is not bool or type(verified) is not bool:
                raise ValueError("FULL_TREE_REVALIDATION_RESULT")
            category = (
                "REVALIDATION_VERIFIED" if ok and verified
                else "REVALIDATION_UNVERIFIED" if ok
                else "REVALIDATION_BLOCKED"
            )
            return self._append_record(
                selected=selected, provider=provider, outcome="TREE_OBSERVED_NO_PLAN",
                reason_category=category, reason=reason, walk_digest=None, plan_digest=None,
                reached_stage=None, direction=None, revalidation_ok=ok,
                revalidation_verified=verified,
            )
        except FullTreeProviderError as exc:
            return self._append_record(
                selected=selected, provider=provider, outcome="TREE_BLOCKED",
                reason_category="PROVIDER_CONTRACT", reason=str(exc), walk_digest=None,
                plan_digest=None, reached_stage=None, direction=None,
                revalidation_ok=None, revalidation_verified=None,
            )

    @staticmethod
    def _classify(walk: object, plan: object | None) -> tuple[str, str | None, object | None]:
        stopped = getattr(walk, "stopped_because", None)
        if stopped is not None:
            return "TREE_STOPPED", "SOURCE_STOP", stopped
        refused = getattr(walk, "refused", None)
        if refused is not None:
            return "TREE_REFUSED_PLAN", "SOURCE_REFUSAL", getattr(refused, "refusal", None)
        if plan is not None:
            return "TREE_CANDIDATE_OBSERVED", None, None
        return "TREE_OBSERVED_NO_PLAN", "NO_SOURCE_PLAN", None

    def _append_record(
        self, *, selected, provider: FullTreeCausalProvider, outcome: str,
        reason_category: str | None, reason: object | None, walk_digest: str | None,
        plan_digest: str | None, reached_stage: str | None, direction: str | None,
        revalidation_ok: bool | None = None, revalidation_verified: bool | None = None,
    ) -> FullTreeReplayResult:
        if outcome not in _OUTCOMES:
            raise ValueError("unknown full-tree outcome")
        trace = provider.public_trace()
        consumed = len(trace)
        unreached = tuple(operation.operation_id for operation in selected.operations[consumed:])
        previous = self._records[-1].record_digest if self._records else _ROOT_DIGEST
        common = {
            "pass_id": selected.pass_id, "decision_time": selected.decision_time.isoformat(),
            "source_variant": selected.source_variant, "outcome": outcome,
            "reached_stage": reached_stage, "direction": direction,
            "reason_category": reason_category, "source_reason_digest": _source_reason_digest(reason),
            "walk_digest": walk_digest, "plan_digest": plan_digest,
            "trace_digest": _digest([dict(item) for item in trace]),
            "unreached_operation_ids": unreached, "previous_record_digest": previous,
            "revalidation_ok": revalidation_ok, "revalidation_verified": revalidation_verified,
        }
        record = FullTreeObservationRecord(**common, record_digest=_digest(common))
        self._records.append(record)
        return FullTreeReplayResult(record=record)

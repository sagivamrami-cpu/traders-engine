"""Public-only checkpoint contracts for full-tree causal replay."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .full_tree_contracts import FullTreeEvidenceBundle, full_tree_manifest_digest
from .full_tree_cross_market_context import FullTreeCrossMarketContextRecord


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class FullTreeProviderBaseline:
    """The public fingerprint needed to resume with the same private bundle."""

    bundle_manifest_digest: str
    baseline_digest: str

    @classmethod
    def capture(cls, bundle: FullTreeEvidenceBundle) -> "FullTreeProviderBaseline":
        if type(bundle) is not FullTreeEvidenceBundle:
            raise ValueError("bundle must be an exact FullTreeEvidenceBundle")
        manifest_digest = full_tree_manifest_digest(bundle)
        return cls(
            bundle_manifest_digest=manifest_digest,
            baseline_digest=_digest({"schema_version": "full-tree-provider-baseline-v1", "bundle_manifest_digest": manifest_digest}),
        )


@dataclass(frozen=True, kw_only=True)
class FullTreeCrossMarketContextBaseline:
    """Public baseline for private GC-flow context sidecars of one bundle."""

    bundle_manifest_digest: str
    baseline_digest: str

    @classmethod
    def capture(
        cls,
        bundle: FullTreeEvidenceBundle,
        records: tuple[FullTreeCrossMarketContextRecord, ...],
    ) -> "FullTreeCrossMarketContextBaseline":
        if type(bundle) is not FullTreeEvidenceBundle or type(records) is not tuple:
            raise ValueError("CROSS_MARKET_BASELINE")
        manifest_digest = full_tree_manifest_digest(bundle)
        if any(type(record) is not FullTreeCrossMarketContextRecord for record in records):
            raise ValueError("CROSS_MARKET_BASELINE")
        if any(record.bundle_manifest_digest != manifest_digest for record in records):
            raise ValueError("CROSS_MARKET_BASELINE")
        pass_ids = [record.pass_id for record in records]
        if len(pass_ids) != len(set(pass_ids)):
            raise ValueError("CROSS_MARKET_BASELINE")
        return cls(
            bundle_manifest_digest=manifest_digest,
            baseline_digest=_digest({
                "schema_version": "full-tree-cross-market-context-baseline-v1",
                "bundle_manifest_digest": manifest_digest,
                "records": [record.commitment() for record in records],
            }),
        )


@dataclass(frozen=True, kw_only=True)
class FullTreeReplayCheckpoint:
    baseline_digest: str
    bundle_manifest_digest: str
    records: tuple[object, ...]
    next_pass_index: int
    last_completed_decision_time: str | None

    def as_dict(self) -> dict[str, object]:
        from .full_tree_replay import observation_record_payload

        return {
            "schema_version": "full-tree-replay-checkpoint-v1",
            "baseline_digest": self.baseline_digest,
            "bundle_manifest_digest": self.bundle_manifest_digest,
            "records": [
                {**observation_record_payload(record), "record_digest": record.record_digest}
                for record in self.records
            ],
            "next_pass_index": self.next_pass_index,
            "last_completed_decision_time": self.last_completed_decision_time,
        }


class FullTreeCheckpointStore:
    """Tiny in-memory holder; persistence remains caller-owned and raw-free."""

    def __init__(self) -> None:
        self._checkpoint: FullTreeReplayCheckpoint | None = None

    def save(self, checkpoint: FullTreeReplayCheckpoint) -> None:
        if type(checkpoint) is not FullTreeReplayCheckpoint:
            raise ValueError("checkpoint must be an exact FullTreeReplayCheckpoint")
        self._checkpoint = checkpoint

    def load(self) -> FullTreeReplayCheckpoint:
        if self._checkpoint is None:
            raise LookupError("FULL_TREE_CHECKPOINT_MISSING")
        return self._checkpoint

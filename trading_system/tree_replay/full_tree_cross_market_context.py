"""Private GC-flow sidecar bound to one existing full-tree evidence pass."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from .cross_market_flow import CrossMarketFlowContext
from .full_tree_contracts import FullTreeEvidenceBundle, full_tree_manifest_digest


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class FullTreeCrossMarketContextRecord:
    """One private context and its public parent/pass provenance commitment."""

    bundle_manifest_digest: str
    pass_id: str
    context: CrossMarketFlowContext = field(repr=False, compare=False, hash=False)

    @classmethod
    def capture(
        cls,
        bundle: FullTreeEvidenceBundle,
        pass_id: str,
        context: CrossMarketFlowContext,
    ) -> "FullTreeCrossMarketContextRecord":
        if type(bundle) is not FullTreeEvidenceBundle or type(context) is not CrossMarketFlowContext:
            raise ValueError("CROSS_MARKET_PARENT")
        try:
            replay_pass = bundle.pass_by_id(pass_id)
        except (KeyError, ValueError) as exc:
            raise ValueError("CROSS_MARKET_PARENT") from exc
        if context.target_instrument != bundle.instrument or context.decision_time != replay_pass.decision_time:
            raise ValueError("CROSS_MARKET_PARENT")
        return cls(
            bundle_manifest_digest=full_tree_manifest_digest(bundle),
            pass_id=replay_pass.pass_id,
            context=context,
        )

    def __post_init__(self) -> None:
        if type(self.bundle_manifest_digest) is not str or len(self.bundle_manifest_digest) != 64:
            raise ValueError("CROSS_MARKET_RECORD")
        if type(self.pass_id) is not str or not self.pass_id:
            raise ValueError("CROSS_MARKET_RECORD")
        if type(self.context) is not CrossMarketFlowContext:
            raise ValueError("CROSS_MARKET_RECORD")

    def commitment(self) -> dict[str, object]:
        return {
            "schema_version": "full-tree-cross-market-context-record-v1",
            "bundle_manifest_digest": self.bundle_manifest_digest,
            "pass_id": self.pass_id,
            "context": self.context.commitment(),
        }

    @property
    def record_digest(self) -> str:
        return _digest(self.commitment())

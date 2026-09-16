from __future__ import annotations

import hashlib
from datetime import timedelta

from trading_system.candidates.contracts import CandidateAction
from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.features.contracts import UnifiedMarketState

GRAPH_ID = "tr-vshape-retest-long"
GRAPH_VERSION = "fixture-graph-rules-0.1.0"
PRODUCER = "TR"
DIRECTION = "LONG"


def _candidate_id(snapshot: UnifiedMarketState) -> str:
    payload = {
        "snapshot_id": snapshot.snapshot_id,
        "producer": PRODUCER,
        "graph_id": GRAPH_ID,
        "graph_version": GRAPH_VERSION,
        "direction": DIRECTION,
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def generate_fixture_candidate(snapshot: UnifiedMarketState, *, created_at) -> CandidateAction:
    reasons: list[str] = []
    return_feature = snapshot.feature_values.get("price.return_pct")
    if snapshot.data_quality != "VALID":
        reasons.append(f"DATA_QUALITY_{snapshot.data_quality}")
    if return_feature is None or return_feature.value is None or return_feature.value <= 0:
        reasons.append("NON_POSITIVE_RETURN")
    else:
        reasons.append("POSITIVE_RETURN")

    status = "ELIGIBLE" if reasons == ["POSITIVE_RETURN"] else "REJECTED"
    return CandidateAction(
        candidate_id=_candidate_id(snapshot),
        snapshot_id=snapshot.snapshot_id,
        producer=PRODUCER,
        graph_id=GRAPH_ID,
        graph_version=GRAPH_VERSION,
        direction=DIRECTION,
        status=status,
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=1),
        reasons=tuple(reasons),
    )

from __future__ import annotations

import hashlib

from trading_system.candidates.contracts import CandidateAction, OutcomeLabel, TradeContract
from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import UnifiedMarketState

DATASET_ID = "fixture-candidate-dataset"
DATASET_VERSION = "fixture-candidate-dataset-0.1.0"
FEATURE_SCHEMA_VERSION = "feature-catalog-0.1.0"


def _feature_values(snapshot: UnifiedMarketState) -> dict:
    return {
        name: feature.to_payload()["value"]
        for name, feature in sorted(snapshot.feature_values.items())
    }


def _exclusion_reasons(candidate: CandidateAction, label: OutcomeLabel | None) -> tuple[str, ...]:
    reasons: list[str] = []
    if candidate.status != "ELIGIBLE":
        reasons.append("CANDIDATE_REJECTED")
    if label is None:
        reasons.append("LABEL_MISSING")
    elif label.label_quality == "EXCLUDED_FROM_TRAINING":
        reasons.append("LABEL_EXCLUDED_FROM_TRAINING")
    return tuple(reasons)


def _row_id(
    snapshot: UnifiedMarketState,
    candidate: CandidateAction,
    contract: TradeContract | None,
    label: OutcomeLabel | None,
    features: dict,
) -> str:
    payload = {
        "snapshot_id": snapshot.snapshot_id,
        "candidate_id": candidate.candidate_id,
        "graph_version": candidate.graph_version,
        "contract_version": contract.contract_version if contract else None,
        "label_version": label.label_version if label else None,
        "features": features,
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_candidate_training_row(
    snapshot: UnifiedMarketState,
    candidate: CandidateAction,
    contract: TradeContract | None,
    label: OutcomeLabel | None,
    *,
    split: str,
    source_hashes: dict[str, str],
) -> CandidateTrainingRow:
    features = _feature_values(snapshot)
    exclusion_reasons = _exclusion_reasons(candidate, label)
    included = candidate.status == "ELIGIBLE" and label is not None and not exclusion_reasons
    return CandidateTrainingRow(
        row_id=_row_id(snapshot, candidate, contract, label, features),
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        snapshot_id=snapshot.snapshot_id,
        candidate_id=candidate.candidate_id,
        symbol=snapshot.symbol,
        observation_time=snapshot.observation_time,
        graph_id=candidate.graph_id,
        graph_version=candidate.graph_version,
        direction=candidate.direction,
        candidate_status=candidate.status,
        features=features,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        contract_version=contract.contract_version if contract else None,
        label_version=label.label_version if label else None,
        outcome_class=label.outcome_class if label else None,
        label_quality=label.label_quality if label else "EXCLUDED_FROM_TRAINING",
        included_in_training=included,
        exclusion_reasons=exclusion_reasons,
        split=split,
        source_hashes=source_hashes,
    )

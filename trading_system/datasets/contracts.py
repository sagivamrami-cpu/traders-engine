from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from trading_system.features.contracts import plain_value, utc_iso


@dataclass(frozen=True)
class CandidateTrainingRow:
    row_id: str
    dataset_id: str
    dataset_version: str
    snapshot_id: str
    candidate_id: str
    symbol: str
    observation_time: datetime
    graph_id: str
    graph_version: str
    direction: str
    candidate_status: str
    features: Mapping[str, Any]
    feature_schema_version: str
    contract_version: str | None
    label_version: str | None
    outcome_class: str | None
    label_quality: str
    included_in_training: bool
    exclusion_reasons: tuple[str, ...]
    split: str
    source_hashes: Mapping[str, str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "snapshot_id": self.snapshot_id,
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "observation_time": utc_iso(self.observation_time),
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "direction": self.direction,
            "candidate_status": self.candidate_status,
            "features": {key: plain_value(value) for key, value in sorted(self.features.items())},
            "feature_schema_version": self.feature_schema_version,
            "contract_version": self.contract_version,
            "label_version": self.label_version,
            "outcome_class": self.outcome_class,
            "label_quality": self.label_quality,
            "included_in_training": self.included_in_training,
            "exclusion_reasons": list(self.exclusion_reasons),
            "split": self.split,
            "source_hashes": dict(sorted(self.source_hashes.items())),
        }

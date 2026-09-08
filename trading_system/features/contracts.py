from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.isoformat().replace("+00:00", "Z")


def plain_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return utc_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_value(item) for item in value]
    return value


@dataclass(frozen=True)
class FeatureValue:
    name: str
    value: Any
    dtype: str
    status: str
    observed_at: datetime
    computed_at: datetime
    source: str
    engine_version: str
    confidence: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": plain_value(self.value),
            "dtype": self.dtype,
            "status": self.status,
            "observed_at": utc_iso(self.observed_at),
            "computed_at": utc_iso(self.computed_at),
            "source": self.source,
            "engine_version": self.engine_version,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class UnifiedMarketState:
    snapshot_id: str
    symbol: str
    observation_time: datetime
    schema_version: str
    data_quality: str
    feature_values: Mapping[str, FeatureValue]
    availability: Mapping[str, bool]
    regime: Mapping[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "symbol": self.symbol,
            "observation_time": utc_iso(self.observation_time),
            "schema_version": self.schema_version,
            "data_quality": self.data_quality,
            "feature_values": {
                name: feature.to_payload() for name, feature in sorted(self.feature_values.items())
            },
            "availability": dict(sorted(self.availability.items())),
            "regime": plain_value(self.regime),
        }

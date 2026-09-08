from __future__ import annotations

import hashlib
from datetime import datetime

from trading_system.data_foundation.contracts import NormalizedBar
from trading_system.data_foundation.point_in_time import latest_bar_at, records_available_at
from trading_system.features.contracts import FeatureValue, UnifiedMarketState
from trading_system.features.price_action import compute_price_action_features
from trading_system.data_foundation.hashing import stable_json_dumps

UNIFIED_MARKET_STATE_VERSION = "unified-market-state-0.1.0"


def _previous_available_record(
    records: list[NormalizedBar],
    symbol: str,
    current: NormalizedBar,
    observation_time: datetime,
) -> NormalizedBar | None:
    candidates = [
        record
        for record in records_available_at(records, observation_time)
        if record.canonical_symbol == symbol and record.observed_at < current.observed_at
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda record: (record.observed_at, record.available_at))


def _data_quality(features: dict[str, FeatureValue]) -> str:
    required = [
        "data.symbol",
        "data.closed_bar",
        "data.freshness_status",
        "price.range_pct",
        "price.body_pct",
    ]
    statuses = {features[name].status for name in required}
    if statuses == {"VALID"}:
        return "VALID"
    if "UNAVAILABLE" in statuses:
        return "INVALID"
    return "DEGRADED"


def _snapshot_id(symbol: str, observation_time: datetime, features: dict[str, FeatureValue]) -> str:
    payload = {
        "symbol": symbol,
        "observation_time": observation_time.isoformat().replace("+00:00", "Z"),
        "features": {name: feature.to_payload() for name, feature in sorted(features.items())},
    }
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_unified_market_state(
    records: list[NormalizedBar],
    symbol: str,
    observation_time: datetime,
    *,
    computed_at: datetime,
) -> UnifiedMarketState:
    current = latest_bar_at(records, symbol, observation_time)
    if current is None:
        raise ValueError(f"no available records for {symbol} at {observation_time.isoformat()}")
    previous = _previous_available_record(records, symbol, current, observation_time)
    features = {
        feature.name: feature
        for feature in compute_price_action_features(current, previous, computed_at=computed_at)
    }
    snapshot_id = _snapshot_id(symbol, observation_time, features)
    return UnifiedMarketState(
        snapshot_id=snapshot_id,
        symbol=symbol,
        observation_time=observation_time,
        schema_version=UNIFIED_MARKET_STATE_VERSION,
        data_quality=_data_quality(features),
        feature_values=features,
        availability={"ohlcv-fixture-v1": True},
        regime={"primary": "FIXTURE_NEUTRAL", "probabilities": {"FIXTURE_NEUTRAL": 1.0}},
    )

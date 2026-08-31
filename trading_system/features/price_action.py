from __future__ import annotations

from datetime import datetime

from trading_system.data_foundation.contracts import NormalizedBar, QualityStatus
from trading_system.features.contracts import FeatureValue

PRICE_ACTION_ENGINE_VERSION = "price-action-engine-0.1.0"
DATA_PROVENANCE_ENGINE_VERSION = "data-provenance-engine-0.1.0"


def phase0_status(status: QualityStatus) -> str:
    if status is QualityStatus.VALID:
        return "VALID"
    if status is QualityStatus.CORRECTED:
        return "VALID"
    if status is QualityStatus.MISSING:
        return "MISSING"
    if status is QualityStatus.STALE:
        return "STALE"
    return "UNAVAILABLE"


def _feature(
    *,
    name: str,
    value,
    dtype: str,
    status: str,
    record: NormalizedBar,
    computed_at: datetime,
    source: str,
    engine_version: str,
    confidence: float = 1.0,
) -> FeatureValue:
    return FeatureValue(
        name=name,
        value=value,
        dtype=dtype,
        status=status,
        observed_at=record.observed_at,
        computed_at=computed_at,
        source=source,
        engine_version=engine_version,
        confidence=confidence,
    )


def compute_price_action_features(
    record: NormalizedBar,
    previous_record: NormalizedBar | None,
    computed_at: datetime,
) -> list[FeatureValue]:
    source_status = phase0_status(record.quality_status)
    features = [
        _feature(
            name="data.symbol",
            value=record.canonical_symbol,
            dtype="string",
            status=source_status,
            record=record,
            computed_at=computed_at,
            source="data-provenance-fixture-engine",
            engine_version=DATA_PROVENANCE_ENGINE_VERSION,
        ),
        _feature(
            name="data.timeframe",
            value="1m",
            dtype="string",
            status=source_status,
            record=record,
            computed_at=computed_at,
            source="data-provenance-fixture-engine",
            engine_version=DATA_PROVENANCE_ENGINE_VERSION,
        ),
        _feature(
            name="data.closed_bar",
            value=True,
            dtype="boolean",
            status=source_status,
            record=record,
            computed_at=computed_at,
            source="data-provenance-fixture-engine",
            engine_version=DATA_PROVENANCE_ENGINE_VERSION,
        ),
        _feature(
            name="data.freshness_status",
            value=source_status,
            dtype="categorical",
            status=source_status,
            record=record,
            computed_at=computed_at,
            source="data-provenance-fixture-engine",
            engine_version=DATA_PROVENANCE_ENGINE_VERSION,
        ),
        _feature(
            name="data.observed_at",
            value=record.observed_at.isoformat().replace("+00:00", "Z"),
            dtype="string",
            status=source_status,
            record=record,
            computed_at=computed_at,
            source="data-provenance-fixture-engine",
            engine_version=DATA_PROVENANCE_ENGINE_VERSION,
        ),
    ]

    price_feature_status = "VALID" if source_status == "VALID" else source_status
    previous_valid = previous_record is not None and phase0_status(previous_record.quality_status) == "VALID"
    if previous_valid:
        return_pct = (record.close - previous_record.close) / previous_record.close
        return_status = price_feature_status
    else:
        return_pct = None
        return_status = "UNAVAILABLE"

    features.extend(
        [
            _feature(
                name="price.return_pct",
                value=return_pct,
                dtype="float" if return_pct is not None else "null",
                status=return_status,
                record=record,
                computed_at=computed_at,
                source="price-action-fixture-engine",
                engine_version=PRICE_ACTION_ENGINE_VERSION,
            ),
            _feature(
                name="price.range_pct",
                value=(record.high - record.low) / record.close if source_status != "UNAVAILABLE" else None,
                dtype="float" if source_status != "UNAVAILABLE" else "null",
                status=price_feature_status,
                record=record,
                computed_at=computed_at,
                source="price-action-fixture-engine",
                engine_version=PRICE_ACTION_ENGINE_VERSION,
            ),
            _feature(
                name="price.body_pct",
                value=abs(record.close - record.open) / record.close if source_status != "UNAVAILABLE" else None,
                dtype="float" if source_status != "UNAVAILABLE" else "null",
                status=price_feature_status,
                record=record,
                computed_at=computed_at,
                source="price-action-fixture-engine",
                engine_version=PRICE_ACTION_ENGINE_VERSION,
            ),
        ]
    )
    return features

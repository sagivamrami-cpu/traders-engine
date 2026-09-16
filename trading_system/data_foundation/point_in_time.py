from __future__ import annotations

from datetime import datetime

from trading_system.data_foundation.contracts import NormalizedBar


def records_available_at(
    records: list[NormalizedBar],
    observation_time: datetime,
) -> list[NormalizedBar]:
    if observation_time.tzinfo is None:
        raise ValueError("observation_time must be timezone-aware")
    available = [
        record
        for record in records
        if record.observed_at <= observation_time and record.available_at <= observation_time
    ]
    return sorted(
        available,
        key=lambda record: (record.observed_at, record.source_id, record.raw_symbol),
    )


def latest_bar_at(
    records: list[NormalizedBar],
    symbol: str,
    observation_time: datetime,
) -> NormalizedBar | None:
    matching = [
        record
        for record in records_available_at(records, observation_time)
        if record.canonical_symbol == symbol
    ]
    if not matching:
        return None
    return max(matching, key=lambda record: (record.observed_at, record.available_at))

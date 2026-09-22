from __future__ import annotations

from trading_system.data_foundation.contracts import AvailabilityInterval, NormalizedBar


def build_availability_intervals(records: list[NormalizedBar]) -> list[AvailabilityInterval]:
    if not records:
        return []

    intervals: list[AvailabilityInterval] = []
    current = records[0]
    start = current.observed_at
    end = current.observed_at
    count = 1
    reasons = set(current.reason_codes)

    previous_observed_at = current.observed_at
    for record in records[1:]:
        if record.observed_at < previous_observed_at:
            raise ValueError("records must be sorted by observed_at")
        previous_observed_at = record.observed_at

        same_group = (
            record.source_id == current.source_id
            and record.canonical_symbol == current.canonical_symbol
            and record.quality_status == current.quality_status
        )
        if same_group:
            end = record.observed_at
            count += 1
            reasons.update(record.reason_codes)
            continue

        intervals.append(
            AvailabilityInterval(
                source_id=current.source_id,
                canonical_symbol=current.canonical_symbol,
                start_observed_at=start,
                end_observed_at=end,
                quality_status=current.quality_status,
                reason_codes=tuple(sorted(reasons)),
                record_count=count,
            )
        )
        current = record
        start = record.observed_at
        end = record.observed_at
        count = 1
        reasons = set(record.reason_codes)

    intervals.append(
        AvailabilityInterval(
            source_id=current.source_id,
            canonical_symbol=current.canonical_symbol,
            start_observed_at=start,
            end_observed_at=end,
            quality_status=current.quality_status,
            reason_codes=tuple(sorted(reasons)),
            record_count=count,
        )
    )
    return intervals

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChronologicalSplitBoundaries:
    train_end: datetime
    validation_end: datetime


def assign_chronological_split(
    observation_time: datetime,
    boundaries: ChronologicalSplitBoundaries,
) -> str:
    if observation_time.tzinfo is None:
        raise ValueError("observation_time must be timezone-aware")
    if boundaries.train_end.tzinfo is None or boundaries.validation_end.tzinfo is None:
        raise ValueError("split boundaries must be timezone-aware")
    if boundaries.train_end >= boundaries.validation_end:
        raise ValueError("train_end must be before validation_end")
    if observation_time <= boundaries.train_end:
        return "TRAIN"
    if observation_time <= boundaries.validation_end:
        return "VALIDATION"
    return "TEST"

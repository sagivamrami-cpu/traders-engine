"""Strict scalar pre-entry inputs; metadata checks are not proof of feed lineage.

Producers must still prove as-of computation and dependency availability. This
boundary cannot detect an outcome falsely registered as a PRE_ENTRY feature.
Missing-observation timestamps describe the evaluation of absence, not a made-up
market event. Stale raw values belong in diagnostics, not model feature values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


STATUSES = frozenset({"KNOWN", "UNKNOWN", "UNAVAILABLE", "NOT_APPLICABLE", "STALE"})


def _nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    dtype: str
    unit: str
    phase: str
    required: bool

    def __post_init__(self) -> None:
        _nonempty(self.feature_id, "feature_id")
        _nonempty(self.unit, "unit")
        if self.dtype not in ("number", "boolean", "category"):
            raise ValueError("dtype must be number, boolean or category")
        if self.phase not in ("PRE_ENTRY", "POST_ENTRY", "OUTCOME"):
            raise ValueError("phase must be PRE_ENTRY, POST_ENTRY or OUTCOME")
        if type(self.required) is not bool:
            raise ValueError("required must be boolean")


@dataclass(frozen=True)
class FeatureObservation:
    feature_id: str
    value: float | int | bool | str | None
    status: str
    observed_at: datetime
    available_at: datetime
    source: str

    def __post_init__(self) -> None:
        _nonempty(self.feature_id, "feature_id")
        _nonempty(self.source, "source")
        if self.status not in STATUSES:
            raise ValueError("unknown availability status")
        if (self.status == "KNOWN") != (self.value is not None):
            raise ValueError("KNOWN requires a value; all other statuses require None")


def _validate_value(definition: FeatureDefinition, observation: FeatureObservation) -> None:
    if observation.status != "KNOWN":
        return
    value = observation.value
    if definition.dtype == "number":
        if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
            raise ValueError(f"{definition.feature_id} requires a finite number, not bool")
    elif definition.dtype == "boolean":
        if type(value) is not bool:
            raise ValueError(f"{definition.feature_id} requires boolean")
    elif type(value) is not str or not value.strip():
        raise ValueError(f"{definition.feature_id} requires a nonempty category")


@dataclass(frozen=True)
class PreEntrySnapshot:
    snapshot_id: str
    decision_time: datetime
    definitions: tuple[FeatureDefinition, ...]
    observations: tuple[FeatureObservation, ...]

    def __post_init__(self) -> None:
        _nonempty(self.snapshot_id, "snapshot_id")
        _aware(self.decision_time)
        object.__setattr__(self, "definitions", tuple(self.definitions))
        object.__setattr__(self, "observations", tuple(self.observations))
        if not self.definitions:
            raise ValueError("empty feature registry cannot form a snapshot")
        definitions = {item.feature_id: item for item in self.definitions}
        observations = {item.feature_id: item for item in self.observations}
        if len(definitions) != len(self.definitions) or len(observations) != len(self.observations):
            raise ValueError("duplicate feature definition or observation")
        if definitions.keys() != observations.keys():
            raise ValueError("missing or unknown feature; represent absence explicitly")
        decision_instant = self.decision_time.astimezone(timezone.utc)
        for definition in self.definitions:
            if definition.phase != "PRE_ENTRY":
                raise ValueError("only PRE_ENTRY definitions may enter this snapshot")
            observation = observations[definition.feature_id]
            _aware(observation.observed_at)
            _aware(observation.available_at)
            # Same-tz datetime comparisons use wall time and can ignore DST fold.
            observed_instant = observation.observed_at.astimezone(timezone.utc)
            available_instant = observation.available_at.astimezone(timezone.utc)
            if observed_instant > decision_instant or available_instant > decision_instant:
                raise ValueError(f"future information in {definition.feature_id}")
            if available_instant < observed_instant:
                raise ValueError("availability cannot be before observation")
            _validate_value(definition, observation)

    @property
    def blocking_features(self) -> tuple[str, ...]:
        required = {item.feature_id for item in self.definitions if item.required}
        return tuple(sorted(
            item.feature_id for item in self.observations
            if item.feature_id in required and item.status != "KNOWN"
        ))

    @property
    def eligible(self) -> bool:
        """Input completeness only, not tree, trade or training approval."""
        return not self.blocking_features

    def to_payload(self) -> dict:
        definitions = {item.feature_id: item for item in self.definitions}
        ordered = sorted(self.observations, key=lambda item: item.feature_id)
        return {
            "schema_version": "tree-pre-entry-snapshot-v1",
            "snapshot_id": self.snapshot_id,
            "decision_time": _utc(self.decision_time),
            "eligible": self.eligible,
            "blocking_features": list(self.blocking_features),
            "features": {item.feature_id: item.value for item in ordered},
            "availability": {item.feature_id: item.status for item in ordered},
            "provenance": {
                item.feature_id: {
                    "observed_at": _utc(item.observed_at),
                    "available_at": _utc(item.available_at),
                    "source": item.source,
                    "dtype": definitions[item.feature_id].dtype,
                    "unit": definitions[item.feature_id].unit,
                    "phase": definitions[item.feature_id].phase,
                    "required": definitions[item.feature_id].required,
                } for item in ordered
            },
        }


def build_snapshot(
    snapshot_id: str,
    decision_time: datetime,
    definitions: Iterable[FeatureDefinition],
    observations: Iterable[FeatureObservation],
) -> PreEntrySnapshot:
    return PreEntrySnapshot(snapshot_id, decision_time, tuple(definitions), tuple(observations))

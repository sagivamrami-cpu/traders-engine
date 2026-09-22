"""Explicit as-of level evidence, not a historical level-map calculator."""
from dataclasses import dataclass
from datetime import datetime

from .bars import _number, _utc, _validate_identity


def _text(value, field):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be a nonempty trimmed string")


@dataclass(frozen=True, kw_only=True)
class NamedLevel:
    name: str
    price: float

    def __post_init__(self):
        _text(self.name, "name")
        value = _number(self.price, "price")
        if value <= 0:
            raise ValueError("price must be positive")
        object.__setattr__(self, "price", value)


@dataclass(frozen=True, kw_only=True)
class LevelSnapshot:
    """Caller-attested level state at observed_at; preserve source order on ties.

    Metadata is not proof that levels were calculated causally. The caller must
    retain dependency evidence and must not timestamp a future-derived level as
    an earlier observation. One snapshot is used for one confirmation, not history.
    """
    snapshot_id: str
    instrument: str
    version: str
    observed_at: datetime
    available_at: datetime
    source: str
    levels: tuple[NamedLevel, ...]

    def __post_init__(self):
        for field in ("snapshot_id", "version", "source"):
            _text(getattr(self, field), field)
        _validate_identity(self.instrument, "5m")
        for field in ("observed_at", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.available_at < self.observed_at:
            raise ValueError("level availability cannot precede observation")
        if type(self.levels) is not tuple or any(not isinstance(x, NamedLevel) for x in self.levels):
            raise ValueError("levels must be a tuple of NamedLevel objects")
        if len({x.name for x in self.levels}) != len(self.levels):
            raise ValueError("duplicate level names and revisions are unsupported")

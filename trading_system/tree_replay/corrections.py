"""Immutable supplied correction evidence assessed at an explicit replay clock.

This records source predicates only. It does not apply offsets, certify a frame,
infer a feed, or admit trades. Both readiness flags remain false.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json

from .bars import _number, _utc, _validate_identity
from .levels import _text
from ._vendor.correction import Correction, broker_shape_ok_at


@dataclass(frozen=True, kw_only=True)
class CorrectionEvidence:
    evidence_id: str
    frame_id: str
    instrument: str
    version: str
    observed_at: datetime
    available_at: datetime
    provenance: str
    offset: float
    source: str
    confidence: str
    note: str
    tv_from: datetime | None = None

    def __post_init__(self) -> None:
        for field in ("evidence_id", "frame_id", "version", "provenance", "source", "confidence"):
            _text(getattr(self, field), field)
        _validate_identity(self.instrument, "5m")
        if not isinstance(self.note, str):
            raise ValueError("note must be a string")
        object.__setattr__(self, "offset", _number(self.offset, "offset"))
        for field in ("observed_at", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.tv_from is not None:
            object.__setattr__(self, "tv_from", _utc(self.tv_from, "tv_from"))
            if self.tv_from > self.observed_at:
                raise ValueError("tv_from cannot follow observed_at")


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def assess_correction_asof(
    correction: CorrectionEvidence | None, *, instrument: str,
    frame_id: str, decision_time: datetime, lookback_days: float,
    max_age_seconds: int,
) -> dict:
    """Validate association and policy before assessing temporal eligibility.

    Unavailable evidence contributes neither payload nor quality flags to the
    canonical result/hash. ASSESSED includes false shape and unverified evidence;
    downstream source consumers retain their own distinct admission rules.
    """
    _validate_identity(instrument, "5m")
    _text(frame_id, "frame_id")
    decision_time = _utc(decision_time, "decision_time")
    lookback_days = _number(lookback_days, "lookback_days")
    if lookback_days < 0:
        raise ValueError("lookback_days must be nonnegative")
    if type(max_age_seconds) is not int or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be a native nonnegative integer")
    if correction is not None:
        if not isinstance(correction, CorrectionEvidence):
            raise ValueError("correction must be CorrectionEvidence or None")
        if correction.instrument != instrument or correction.frame_id != frame_id:
            raise ValueError("correction must match the exact instrument and frame_id")

    blocker = None
    if correction is None:
        blocker = "CORRECTION_MISSING"
    elif correction.observed_at > decision_time:
        blocker = "CORRECTION_FUTURE_OBSERVATION"
    elif correction.available_at > decision_time:
        blocker = "CORRECTION_UNAVAILABLE"
    elif (decision_time - correction.observed_at).total_seconds() > max_age_seconds:
        blocker = "CORRECTION_STALE"

    evidence = unverified = shape_ok = None
    if blocker is None:
        evidence = {
            key: _iso(value) if isinstance(value, datetime) else value
            for key, value in asdict(correction).items()
        }
        source_correction = Correction(
            symbol=correction.instrument, offset=correction.offset,
            source=correction.source, confidence=correction.confidence,
            note=correction.note, tv_from=correction.tv_from,
        )
        unverified = source_correction.unverified
        shape_ok = broker_shape_ok_at(source_correction, lookback_days, decision_time=decision_time)

    result = {
        "schema_version": "correction-asof-v1",
        "calculation_version": "chartdesk-correction-asof-v1",
        "instrument": instrument, "frame_id": frame_id,
        "decision_time": _iso(decision_time), "lookback_days": lookback_days,
        "max_age_seconds": max_age_seconds,
        "status": "BLOCKED" if blocker else "ASSESSED", "blocker": blocker,
        "evidence": evidence, "unverified": unverified, "broker_shape_ok": shape_ok,
        "ready_for_replay": False, "ready_for_training": False,
    }
    result["evidence_hash"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return result

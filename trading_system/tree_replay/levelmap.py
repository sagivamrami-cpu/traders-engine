"""Offline historical level maps from causal frames and supplied corrections.

The pinned graph owns family calculations, fetch order and asymmetric gates.
This boundary owns input identity, temporal availability and evidence; a built
map is never producer admission or replay/training readiness.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math

import pandas as pd

from .bars import _utc, _validate_identity
from .corrections import CorrectionEvidence, assess_correction_asof
from .frames import FrameSpec, build_frame_asof
from .levels import LevelSnapshot, NamedLevel
from ._vendor.correction import Correction, broker_shape_ok_at
from ._vendor.levelmap_build import build_at


VERSION = "historical-levelmap-asof-v1"
PREFIX_VERSION = "historical-levelmap-prefix-asof-v1"
_REQUEST_KEYS = frozenset({("1d", 400), ("5m", 3), ("1h", 20),
                           ("15m", 20), ("1h", 240), ("4h", 240)})


@dataclass(frozen=True, kw_only=True)
class MapFrameRequest:
    timeframe: str
    lookback_days: int
    frame: FrameSpec
    correction: CorrectionEvidence | None
    max_correction_age_seconds: int

    def __post_init__(self):
        if (not isinstance(self.timeframe, str) or type(self.lookback_days) is not int
                or (self.timeframe, self.lookback_days) not in _REQUEST_KEYS):
            raise ValueError("only original timeframe/lookback request keys are supported")
        if not isinstance(self.frame, FrameSpec):
            raise ValueError("frame must be a FrameSpec")
        if self.frame.timeframe != self.timeframe:
            raise ValueError("frame must match the exact request timeframe")
        if type(self.max_correction_age_seconds) is not int or self.max_correction_age_seconds < 0:
            raise ValueError("max_correction_age_seconds must be a native nonnegative integer")
        if self.correction is not None:
            if not isinstance(self.correction, CorrectionEvidence):
                raise ValueError("correction must be CorrectionEvidence or None")
            if (self.correction.instrument != self.frame.instrument
                    or self.correction.frame_id != self.frame.frame_id):
                raise ValueError("correction must match exact frame instrument and frame_id")


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


class _DataUnavailable(Exception):
    """Caught only where the original source graph catches fetch failures."""


class _OfflineSource:
    def __init__(self, instrument, decision, requests, closed_base_prefix=False):
        self.instrument = instrument
        self.decision = decision
        self.requests = {(r.timeframe, r.lookback_days): r for r in requests}
        self.fetch_trace = []
        self.shape_trace = []
        self.corrections = {}
        self.error = None
        self.closed_base_prefix = closed_base_prefix

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        if symbol != self.instrument:
            raise ValueError("source requested a different instrument")
        trace = dict(timeframe=timeframe, lookback_days=lookback_days, frame_id=None,
                     status="BLOCKED", blocker=None, policies=None, frame=None, correction=None)
        self.fetch_trace.append(trace)
        req = self.requests.get((timeframe, lookback_days))
        if req is None:
            trace["blocker"] = "REQUEST_MISSING"
            raise _DataUnavailable(trace["blocker"])
        trace["frame_id"] = req.frame.frame_id
        trace["policies"] = dict(max_frame_age_seconds=req.frame.max_age_seconds,
                                 max_correction_age_seconds=req.max_correction_age_seconds)
        try:
            frame = build_frame_asof(req.frame, decision_time=self.decision,
                                     closed_base_prefix=self.closed_base_prefix)
            # Blocked frame hashes may describe unavailable metadata. Only
            # available frame evidence is a selected price dependency.
            trace["frame"] = dict(status=frame["status"], blocker=frame["blocker"])
            if frame["status"] != "AVAILABLE":
                trace["blocker"] = frame["blocker"]
                raise _DataUnavailable(trace["blocker"])
            trace["frame"].update(
                evaluation_sha256=frame["evaluation_sha256"], row_count=len(frame["rows"]),
                observed_at=frame["observed_at"], available_at=frame["available_at"],
                last_row={k: frame["rows"][-1][k] for k in (
                    "source_index_at", "opened_at", "closed_at", "observed_at", "available_at", "state")})
            if self.closed_base_prefix:
                trace["frame"]["observation_cutoff"] = frame["observation_cutoff"]
            assessment = assess_correction_asof(
                req.correction, instrument=self.instrument, frame_id=req.frame.frame_id,
                decision_time=self.decision, lookback_days=0,
                max_age_seconds=req.max_correction_age_seconds)
            trace["correction"] = assessment
            if assessment["status"] != "ASSESSED":
                trace["blocker"] = assessment["blocker"]
                raise _DataUnavailable(trace["blocker"])
            evidence = req.correction
            corr = Correction(symbol=evidence.instrument, offset=evidence.offset,
                              source=evidence.source, confidence=evidence.confidence,
                              note=evidence.note, tv_from=evidence.tv_from)
            rows = frame["rows"]
            df = pd.DataFrame([{k: row[k] for k in ("open", "high", "low", "close", "volume")}
                               for row in rows],
                              index=pd.to_datetime([row["source_index_at"] for row in rows], utc=True))
            # Keep the object alive and its request association local to this
            # invocation. Source shape calls use this exact supplied correction.
            self.corrections[id(corr)] = (corr, len(self.fetch_trace)-1)
            trace["status"] = "AVAILABLE"
            return df, corr
        except _DataUnavailable:
            raise
        except Exception as exc:
            # The original graph can catch optional fetch exceptions. Preserve
            # that boundary while preventing an unexpected adapter error from
            # being presented as a successfully calculated map.
            trace["blocker"] = "FRAME_CALCULATION_ERROR"
            self.error = dict(stage="fetch", exception_type=type(exc).__name__,
                              timeframe=timeframe, lookback_days=lookback_days)
            raise

    def broker_shape_ok(self, corr, days):
        _, index = self.corrections[id(corr)]
        result = broker_shape_ok_at(corr, days, decision_time=self.decision)
        trace = self.fetch_trace[index]
        self.shape_trace.append(dict(
            fetch_index=index, frame_id=trace["frame_id"], lookback_days=days,
            decision_time=_iso(self.decision), broker_shape_ok=result,
            correction_evidence_hash=trace["correction"]["evidence_hash"]))
        return result


def build_levelmap_asof(*, instrument: str, decision_time: datetime,
                       requests: tuple[MapFrameRequest, ...], closed_base_prefix: bool = False) -> dict:
    """Evaluate the complete pinned map at T using only requested local inputs.

    Trace policies and evidence are selected lazily, so unused fallback values
    cannot affect the result hash. All request identities are validated even
    when the graph will not fetch them. No offsets are applied to supplied bars.
    Opt-in prefix mode uses actual T for source gates and publication, while
    constructing prices only through each frame's latest complete base close.
    """
    if type(closed_base_prefix) is not bool:
        raise ValueError("closed_base_prefix must be a bool")
    _validate_identity(instrument, "5m")
    decision = _utc(decision_time, "decision_time")
    if type(requests) is not tuple or any(not isinstance(r, MapFrameRequest) for r in requests):
        raise ValueError("requests must be a tuple of MapFrameRequest objects")
    if any(r.frame.instrument != instrument for r in requests):
        raise ValueError("all frames must match the exact map instrument")
    if len({(r.timeframe, r.lookback_days) for r in requests}) != len(requests):
        raise ValueError("duplicate request keys are unsupported")
    if len({r.frame.frame_id for r in requests}) != len(requests):
        raise ValueError("duplicate frame IDs are unsupported")

    source = _OfflineSource(instrument, decision, requests, closed_base_prefix)
    version = PREFIX_VERSION if closed_base_prefix else VERSION
    result = dict(schema_version=version, calculation_version=version,
                  instrument=instrument, decision_time=_iso(decision), status="BLOCKED",
                  blocker=None, diagnostic=None, levels=[], level_snapshot=None,
                  level_correction=None, source_missing=[], fetch_trace=source.fetch_trace,
                  shape_trace=source.shape_trace, tradeable=False,
                  ready_for_replay=False, ready_for_training=False)
    try:
        levels, corr = build_at(instrument, result["source_missing"], source=source, decision_time=decision)
    except Exception as exc:
        levels, corr = [], None
        result["blocker"] = "SOURCE_CALCULATION_ERROR"
        result["diagnostic"] = dict(stage="build", exception_type=type(exc).__name__)

    if source.error is not None:
        result["blocker"] = "FRAME_CALCULATION_ERROR"
        result["diagnostic"] = source.error
    elif result["blocker"] is None and corr is None:
        result["blocker"] = "REQUIRED_DAILY_INPUT_UNAVAILABLE"

    if result["blocker"] is None:
        public_levels, named = [], []
        for level in levels:
            if not math.isfinite(level.price) or level.price <= 0:
                result["blocker"] = "INVALID_SOURCE_LEVEL"
                result["diagnostic"] = dict(level_name=level.name, reason="price must be finite and positive")
                break
            value = dict(name=level.name, price=float(level.price), kind=level.kind)
            public_levels.append(value)
            named.append(dict(name=value["name"], price=value["price"], level_id="level:"+_hash(value)))
        if result["blocker"] is None:
            snapshot_data = dict(
                instrument=instrument, version=version, source="offline-pinned-levelmap",
                observed_at=_iso(decision), available_at=_iso(decision), levels=named)
            snapshot_data["snapshot_id"] = "levelmap:"+_hash(dict(
                snapshot=snapshot_data, fetch_trace=source.fetch_trace, shape_trace=source.shape_trace))
            try:
                LevelSnapshot(**{**snapshot_data, "observed_at": decision, "available_at": decision,
                                  "levels": tuple(NamedLevel(**v) for v in named)})
            except ValueError as exc:
                result["blocker"] = "INVALID_SOURCE_LEVEL"
                result["diagnostic"] = dict(reason=str(exc))
            else:
                result.update(status="BUILT_UNADMITTED", levels=public_levels,
                              level_snapshot=snapshot_data,
                              level_correction=source.fetch_trace[0]["correction"])

    result["evaluation_sha256"] = _hash(result)
    return result

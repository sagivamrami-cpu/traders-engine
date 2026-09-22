"""Typed, offline decision-time bridge to the pinned reversal producer.

The original find owns internal gates, event selection and winner-only pricing.
This adapter supplies causal frames/maps and records evidence; it admits no
trade, performs no external reads, and reconstructs no market-watch state.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from .bars import _DURATIONS, _utc, _validate_identity
from .corrections import CorrectionEvidence
from .frames import FrameSpec
from .levelmap import MapFrameRequest, _DataUnavailable, _OfflineSource, build_levelmap_asof
from .levels import _text
from .pricing import SUPPORTED_INSTRUMENTS, _pricing_snapshot, _source_plan
from .reversal import SOURCE_COMMIT, _candidate_snapshot, _hash, _numeric_frame, _time
from ._vendor import level_reversal, pricing, pvsra, reversal_producer
from ._vendor.correction import Correction
from ._vendor.levelmap_build import NamedLevel


VERSION = "tree-reversal-producer-asof-v1"


@dataclass(frozen=True, kw_only=True)
class ReversalFrameRequest:
    frame: FrameSpec
    correction: CorrectionEvidence | None
    max_correction_age_seconds: int

    def __post_init__(self):
        if type(self.frame) is not FrameSpec or self.frame.timeframe not in ("5m", "15m"):
            raise ValueError("frame must be an exact 5m or 15m FrameSpec")
        if type(self.max_correction_age_seconds) is not int or self.max_correction_age_seconds < 0:
            raise ValueError("max_correction_age_seconds must be a native nonnegative integer")
        if self.correction is not None:
            if type(self.correction) is not CorrectionEvidence:
                raise ValueError("correction must be CorrectionEvidence or None")
            if (self.correction.instrument != self.frame.instrument
                    or self.correction.frame_id != self.frame.frame_id):
                raise ValueError("correction must match exact frame instrument and frame_id")

    @property
    def timeframe(self):
        return self.frame.timeframe

    @property
    def lookback_days(self):
        return 10


def _validate_requests(instrument, map_requests, reversal_requests):
    for requests, cls in ((map_requests, MapFrameRequest),
                          (reversal_requests, ReversalFrameRequest)):
        if type(requests) is not tuple or any(type(r) is not cls for r in requests):
            raise ValueError(f"requests must be a tuple of exact {cls.__name__} objects")
        for req in requests:
            # Validate even unused bindings before any lazy source call.
            req.__post_init__()
            if type(req.frame) is not FrameSpec:
                raise ValueError("frame must be an exact FrameSpec")
            if req.correction is not None and type(req.correction) is not CorrectionEvidence:
                raise ValueError("correction must be an exact CorrectionEvidence")
            if req.frame.instrument != instrument:
                raise ValueError("all frames must match the exact producer instrument")
        if len({(r.timeframe, r.lookback_days) for r in requests}) != len(requests):
            raise ValueError("duplicate request timeframe/lookback keys")
    all_requests = map_requests + reversal_requests
    if len({r.frame.frame_id for r in all_requests}) != len(all_requests):
        raise ValueError("duplicate map/producer frame IDs")


class _MapBridge:
    def __init__(self, instrument, decision, requests):
        self.instrument, self.decision, self.requests = instrument, decision, requests
        self.report = None
        self.gate = None

    def build(self, symbol):
        if symbol != self.instrument:
            raise ValueError("source requested a different map instrument")
        self.report = build_levelmap_asof(instrument=symbol, decision_time=self.decision,
                                         requests=self.requests, closed_base_prefix=True)
        if self.report["status"] != "BUILT_UNADMITTED":
            self.gate = dict(passed=False, reason=self.report["blocker"])
            return [], None
        evidence = self.report["level_correction"]["evidence"]
        corr = Correction(symbol=evidence["instrument"], offset=evidence["offset"],
                          source=evidence["source"], confidence=evidence["confidence"],
                          note=evidence["note"],
                          tv_from=pd.Timestamp(evidence["tv_from"]) if evidence["tv_from"] else None)
        levels = [NamedLevel(**v) for v in self.report["levels"]]
        reason = "EMPTY_LEVEL_MAP" if not levels else "DAILY_CORRECTION_UNVERIFIED" if corr.unverified else None
        self.gate = dict(passed=reason is None, reason=reason, source=corr.source,
                         unverified=corr.unverified)
        return levels, corr


class _ProducerSource(_OfflineSource):
    """Package-internal use of the accepted frame/trace/exception boundary."""

    def __init__(self, instrument, decision, requests):
        super().__init__(instrument, decision, requests, closed_base_prefix=True)
        self.frames = {}

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        frame, corr = super().fetch_corrected(symbol, timeframe, lookback_days)
        trace = self.fetch_trace[-1]
        try:
            reason = "CORRECTION_UNVERIFIED" if corr.unverified else "CORRECTION_SOURCE_NONE" if corr.source == "none" else None
            trace["producer_gate"] = dict(passed=reason is None, reason=reason,
                                          source=corr.source, unverified=corr.unverified)
            # This trace describes actual attributes. find_at still owns the gate.
            if reason is None:
                closed = frame[frame.index + _DURATIONS[timeframe] <= self.decision]
                trace["closed_rows"] = len(closed)
                # No completed target rows is a detector warmup, not a claim
                # about absent volume on a completed candle.
                if len(closed) and (closed.volume.isna().any() or not (closed.volume > 0).any()):
                    trace.update(status="BLOCKED", blocker="VOLUME_UNAVAILABLE")
                    raise _DataUnavailable("VOLUME_UNAVAILABLE")
                _numeric_frame(tuple(closed.rename_axis("opened_at").reset_index().itertuples(index=False)))
            self.frames[timeframe] = frame
            return frame, corr
        except _DataUnavailable:
            raise
        except Exception as exc:
            # Original find catches every fetch exception. Cover all post-fetch
            # work (including index arithmetic), so such errors cannot become
            # an AVAILABLE trace and a misleading quiet-market result.
            trace.update(status="BLOCKED", blocker="PRODUCER_CALCULATION_ERROR")
            self.error = dict(stage="detector_history", exception_type=type(exc).__name__,
                              timeframe=timeframe, lookback_days=lookback_days)
            raise


def _event_payload(event, vector, *, snapshot_id, decision):
    producer = f"chartdesk.level_reversal.{event.timeframe}"
    candidate_id = _hash(dict(source_commit=SOURCE_COMMIT, producer=producer,
                              source_event_id=event.event_id, confirmed_at=event.confirmed_at))
    payload = asdict(event)
    payload["source_event_id"] = payload.pop("event_id")
    payload["source_direction"] = payload["direction"]
    payload["direction"] = {"לונג": "LONG", "שורט": "SHORT"}[event.direction]
    for key in ("vector_open_time", "confirmation_open_time", "confirmed_at"):
        payload[key] = _time(payload[key])
    payload.update(producer=producer, candidate_id=candidate_id, tradeable=False,
                   source_plan=None, pricing_status="NOT_SELECTED", pricing_snapshot=None,
                   snapshot=_candidate_snapshot(
                       event, vector, snapshot_id=f"{snapshot_id}:{candidate_id}",
                       decision_time=decision, observed_at=decision, available_at=decision,
                       source=f"chart-desk@{SOURCE_COMMIT};{VERSION}"))
    return payload


@dataclass(frozen=True)
class _ReversalEvaluation:
    """Detached evidence plus original mutable selection owned by this evaluation."""

    report: dict
    selected_event: level_reversal.Reversal | None
    selected_plan: pricing.Plan | None


def find_reversal_asof(*, snapshot_id: str, instrument: str,
                      decision_time: datetime,
                      map_requests: tuple[MapFrameRequest, ...],
                      reversal_requests: tuple[ReversalFrameRequest, ...]) -> dict:
    """Evaluate original internal find using supplied causal evidence at actual T.

    All input identities are validated up front; payload dependencies remain lazy.
    Candidates group source episodes across evaluations. decision_id and the
    canonical evaluation hash identify this decision's evidence and snapshot.
    """
    return _evaluate_reversal_asof(
        snapshot_id=snapshot_id, instrument=instrument, decision_time=decision_time,
        map_requests=map_requests, reversal_requests=reversal_requests).report


def _evaluate_reversal_asof(*, snapshot_id: str, instrument: str,
                            decision_time: datetime,
                            map_requests: tuple[MapFrameRequest, ...],
                            reversal_requests: tuple[ReversalFrameRequest, ...]) -> _ReversalEvaluation:
    """Retain actual source objects only after successful selection serialization."""
    _text(snapshot_id, "snapshot_id")
    _validate_identity(instrument, "5m")
    decision = _utc(decision_time, "decision_time")
    _validate_requests(instrument, map_requests, reversal_requests)
    source = _ProducerSource(instrument, decision, reversal_requests)
    bridge = _MapBridge(instrument, decision, map_requests)
    result = dict(schema_version=VERSION, calculation_version=VERSION,
                  source_commit=SOURCE_COMMIT, snapshot_id=snapshot_id,
                  instrument=instrument, decision_time=_time(decision),
                  status="NO_CANDIDATE", blocker=None, reason=None, diagnostic=None,
                  map_report=None, map_gate=None, fetch_trace=source.fetch_trace,
                  shape_trace=source.shape_trace, detection_trace=[], candidates=[], selected=None,
                  tradeable=False, ready_for_replay=False, ready_for_training=False,
                  calculation=dict(pandas_version=pd.__version__, numpy_version=np.__version__,
                                   pvsra_mode="default_non_auction"),
                  missing_stages=["outer_market_watch_admission", "tracker_episode_state",
                                  "cross_producer_arbitration", "execution_and_outcomes",
                                  "full_tree_dataset_training"])
    stage = "map"
    selected_event = selected_plan = None

    def detect(symbol, timeframe, frame, levels, *, now, max_age_s):
        nonlocal stage
        stage = "detection"
        closed = frame[frame.index + _DURATIONS[timeframe] <= now]
        trace = dict(timeframe=timeframe, decision_time=_time(now), max_age_s=max_age_s,
                     closed_rows=len(closed), status="EVALUATED", reason=None, candidates=[])
        result["detection_trace"].append(trace)
        try:
            events = level_reversal.detect_frame(symbol, timeframe, frame, levels,
                                                  now=now, max_age_s=max_age_s)
            vectors = pvsra.pvsra(closed) if events else None
            for event in events:
                candidate = _event_payload(event, vectors.loc[event.vector_open_time],
                                           snapshot_id=snapshot_id, decision=decision)
                result["candidates"].append(candidate)
                trace["candidates"].append(candidate["candidate_id"])
            trace["reason"] = "WARMUP" if len(closed) < 12 else "DETECTED" if events else "NO_CANDIDATE"
        except Exception:
            trace.update(status="BLOCKED", reason="PRODUCER_CALCULATION_ERROR")
            raise
        stage = "pricing"
        return events

    if instrument not in SUPPORTED_INSTRUMENTS:
        result.update(status="BLOCKED", blocker="PRODUCER_UNSUPPORTED_INSTRUMENT")
    else:
        try:
            with np.errstate(over="raise", invalid="raise", divide="ignore"):
                selected = reversal_producer.find_at(instrument, decision_time=decision,
                    source=source, map_source=bridge, detector=detect)
                result.update(map_report=bridge.report, map_gate=bridge.gate)
                if source.error is not None:
                    result.update(status="BLOCKED", blocker="PRODUCER_CALCULATION_ERROR",
                                  diagnostic=source.error)
                elif bridge.report["status"] == "BLOCKED":
                    result.update(status="BLOCKED", blocker=bridge.report["blocker"],
                                  diagnostic=bridge.report["diagnostic"])
                elif selected is not None:
                    event, plan = selected
                    stage = "pricing_serialization"
                    payload = _source_plan(plan, pricing.entry_zone(instrument, plan.entry))
                    chosen = next(c for c in result["candidates"]
                                  if c["timeframe"] == event.timeframe
                                  and c["source_event_id"] == event.event_id
                                  and c["confirmed_at"] == _time(event.confirmed_at))
                    chosen.update(source_plan=payload,
                        pricing_status="PRICE_ACCEPTED_UNADMITTED" if payload["source_tradeable"] else "PRICE_REFUSED",
                        pricing_snapshot=_pricing_snapshot(payload,
                            snapshot_id=f"{snapshot_id}:pricing:{chosen['candidate_id']}",
                            decision_time=decision, observed_at=decision, available_at=decision,
                            source=f"chart-desk@{SOURCE_COMMIT};{VERSION}"))
                    result.update(status="PRODUCER_SELECTED_UNADMITTED", selected=deepcopy(chosen))
                    selected_event, selected_plan = event, plan
                elif not bridge.gate["passed"]:
                    result["reason"] = bridge.gate["reason"]
                elif any(t["status"] == "BLOCKED" for t in source.fetch_trace):
                    result.update(status="NO_SELECTION_INPUTS_UNAVAILABLE", reason="TIMEFRAME_INPUTS_UNAVAILABLE")
                else:
                    result["reason"] = "NO_SOURCE_SELECTION"
        except Exception as exc:
            selected_event = selected_plan = None
            result.update(status="BLOCKED", blocker="PRODUCER_CALCULATION_ERROR", selected=None,
                          map_report=bridge.report, map_gate=bridge.gate,
                          diagnostic=dict(stage=stage, exception_type=type(exc).__name__))
    result["decision_id"] = "reversal-decision:" + _hash(result)
    result["evaluation_sha256"] = _hash(result)
    return _ReversalEvaluation(result, selected_event, selected_plan)

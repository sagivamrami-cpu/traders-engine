"""Pinned setup detection on as-of inputs. No pricing, admission, fills or labels."""
from dataclasses import asdict
from datetime import datetime, timedelta
import hashlib
import json
import math

import numpy as np
import pandas as pd

from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
from .bars import select_closed_bars
from .levels import LevelSnapshot, _text


SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
ADAPTER_VERSION = "chartdesk-closed-level-reversal-v2"


def _time(value):
    return value.isoformat().replace("+00:00", "Z")


def _hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                         default=lambda x: _time(x) if isinstance(x, datetime) else x)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _numeric_frame(bars):
    """Refuse overflow before it can masquerade as a PVSRA climax or midpoint."""
    try:
        total = math.fsum(b.volume for b in bars)
        if not math.isfinite(total):
            raise ValueError("numeric overflow in volume total")
        for b in bars:
            if not math.isfinite((b.high - b.low) * b.volume) or not math.isfinite(b.high + b.low):
                raise ValueError("numeric overflow in spread-volume or midpoint")
    except OverflowError as exc:
        raise ValueError("numeric overflow in PVSRA inputs") from exc
    return pd.DataFrame({key: [getattr(b, key) for b in bars]
                         for key in ("open", "high", "low", "close", "volume")},
                        index=pd.DatetimeIndex([b.opened_at for b in bars]))


def _candidate_snapshot(event, vector, *, snapshot_id, decision_time, available_at, source,
                        observed_at=None):
    # Ratio can be undefined when all prior volumes are zero. Preserve source
    # classification, but never serialize infinity or substitute a made-up zero.
    ratio = float(vector["vol_ratio"])
    ratio = ratio if math.isfinite(ratio) else None
    fields = [
        ("level_price", event.level_price, "number", "price"),
        ("level_name", event.level_name, "category", "source_level_name"),
        ("approach", event.approach, "category", "source_direction_of_arrival"),
        ("pattern", event.pattern, "category", "source_pattern"),
        ("vector_kind", event.vector_kind, "category", "pvsra_kind"),
        ("vector_volume", float(vector["volume"]), "number", "input_volume_units"),
        ("vector_prior_avg_volume_10", float(vector["avg_volume_10"]), "number", "input_volume_units"),
        ("vector_volume_ratio", ratio, "number", "ratio"),
        ("vector_spread_volume", float(vector["spread_volume"]), "number", "price_times_input_volume"),
        ("vector_prior_max_spread_volume_10", float(vector["max_sv_10"]), "number", "price_times_input_volume"),
        ("vector_climax", bool(vector["climax"]), "boolean", "boolean"),
        ("vector_rising", bool(vector["rising"]), "boolean", "boolean"),
        ("sweep_extreme", event.sweep_extreme, "number", "price"),
        ("confirmation_close", event.close, "number", "price"),
    ]
    definitions, observations = [], []
    for name, value, dtype, unit in fields:
        feature_id = f"reversal.{name}"
        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
        observations.append(FeatureObservation(
            feature_id, value, "UNKNOWN" if value is None else "KNOWN",
            event.confirmed_at if observed_at is None else observed_at, available_at, source))
    return build_snapshot(snapshot_id, decision_time, definitions, observations).to_payload()


def detect_reversals_asof(bars, *, snapshot_id, instrument, timeframe, decision_time,
                          history_start, max_age_seconds, level_snapshot,
                          max_level_age_seconds, session_schedule=None) -> dict:
    """Evaluate only the newest selected confirmation using caller-supplied levels.

    Selector and freshness failures are research input blockers, not source trade
    rejections. Budgets must be explicitly chosen by the caller. This does not
    reproduce the whole live find/build_plan/arbiter lifecycle or partial bars.
    """
    _text(snapshot_id, "snapshot_id")
    if timeframe not in ("5m", "15m"):
        raise ValueError("level reversal supports only 5m and 15m")
    if type(max_level_age_seconds) is not int or max_level_age_seconds <= 0:
        raise ValueError("max_level_age_seconds must be an explicit positive integer")
    if level_snapshot is not None:
        if not isinstance(level_snapshot, LevelSnapshot):
            raise ValueError("level_snapshot must be LevelSnapshot or None")
        if level_snapshot.instrument != instrument:
            raise ValueError("levels must match the exact instrument")

    params = dict(instrument=instrument, timeframe=timeframe, decision_time=decision_time,
                  history_start=history_start, max_age_seconds=max_age_seconds)
    if session_schedule is None:
        window = select_closed_bars(bars, **params)
    else:
        from .session_bars import select_session_bars
        window = select_session_bars(bars, **params, session_schedule=session_schedule)
    window_hash = _hash(asdict(window))
    level_hash = _hash(asdict(level_snapshot)) if level_snapshot is not None else None
    evaluation_hash = _hash(dict(window_sha256=window_hash, levels_sha256=level_hash,
                                max_level_age_seconds=max_level_age_seconds,
                                source_commit=SOURCE_COMMIT, adapter_version=ADAPTER_VERSION,
                                pandas_version=pd.__version__, numpy_version=np.__version__))
    blocker = window.blocker
    if blocker is None:
        if level_snapshot is None or level_snapshot.available_at > window.decision_time:
            blocker = "LEVELS_UNAVAILABLE"
        elif level_snapshot.observed_at > window.bars[-1].closed_at:
            blocker = "LEVELS_AFTER_CONFIRMATION"
        elif (window.decision_time - level_snapshot.observed_at) // timedelta(microseconds=1) > max_level_age_seconds * 1_000_000:
            blocker = "LEVELS_STALE"
        elif len(window.bars) < 12:
            blocker = "WARMUP"
        elif any(b.volume is None for b in window.bars) or not any(b.volume > 0 for b in window.bars):
            blocker = "VOLUME_UNAVAILABLE"

    result = dict(schema_version="tree-unpriced-reversal-v1", snapshot_id=snapshot_id,
                  instrument=instrument, timeframe=timeframe, decision_time=_time(window.decision_time),
                  producer=f"chartdesk.level_reversal.{timeframe}",
                  status="BLOCKED" if blocker else "NO_CANDIDATE", blocker=blocker,
                  candidates=[], window_sha256=window_hash, levels_sha256=level_hash,
                  evaluation_sha256=evaluation_hash, history_start=_time(window.history_start),
                  max_age_seconds=max_age_seconds, max_level_age_seconds=max_level_age_seconds,
                  selected_bars=len(window.bars),
                  calculation=dict(source_commit=SOURCE_COMMIT, adapter_version=ADAPTER_VERSION,
                                   pvsra_mode="default_non_auction", pandas_version=pd.__version__,
                                   numpy_version=np.__version__),
                  missing_stages=["historical_level_map", "trade_plan_pricing", "admission",
                                  "producer_arbitration", "execution_and_outcomes"],
                  ready_for_replay=False, ready_for_training=False)
    if session_schedule is not None:
        result["calendar"] = dict(calendar_id=session_schedule.calendar_id,
                                  version=session_schedule.version, source=session_schedule.source,
                                  schedule_sha256=window.schedule_sha256,
                                  available_at=_time(window.calendar_available_at),
                                  expected_bars=window.expected_bars,
                                  missing_opens=[_time(t) for t in window.missing_opens],
                                  out_of_session_bars=window.out_of_session_bars,
                                  straddling_bars=window.straddling_bars,
                                  execution_truth=False)
    # Never expose future raw level values as usable evidence.
    if level_snapshot is not None and level_snapshot.available_at <= window.decision_time:
        result["level_evidence"] = dict(snapshot_id=level_snapshot.snapshot_id,
                                       source=level_snapshot.source, version=level_snapshot.version,
                                       observed_at=_time(level_snapshot.observed_at),
                                       available_at=_time(level_snapshot.available_at),
                                       count=len(level_snapshot.levels))
    if blocker:
        return result

    from ._vendor import level_reversal, pvsra
    frame = _numeric_frame(window.bars)
    try:
        with np.errstate(over="raise", invalid="raise", divide="ignore"):
            detected = level_reversal.detect_frame(instrument, timeframe, frame,
                                                   level_snapshot.levels,
                                                   now=window.decision_time, max_age_s=None)
            vectors = pvsra.pvsra(frame)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("numeric overflow in pinned PVSRA calculation") from exc
    available = max(level_snapshot.available_at, *(b.available_at for b in window.bars))
    if session_schedule is not None:
        available = max(available, window.calendar_available_at)
    source = f"chart-desk@{SOURCE_COMMIT};{ADAPTER_VERSION};evaluation={evaluation_hash}"
    for event in detected:
        if event.confirmed_at != window.bars[-1].closed_at:
            continue
        candidate_id = _hash(dict(source_commit=SOURCE_COMMIT, producer=result["producer"],
                                  source_event_id=event.event_id, confirmed_at=event.confirmed_at))
        payload = asdict(event)
        payload["source_event_id"] = payload.pop("event_id")
        payload["source_direction"] = payload["direction"]
        payload["direction"] = {"לונג": "LONG", "שורט": "SHORT"}[event.direction]
        for key in ("vector_open_time", "confirmation_open_time", "confirmed_at"):
            payload[key] = _time(payload[key])
        payload.update(candidate_id=candidate_id, tradeable=False, trade_plan=None,
                       snapshot=_candidate_snapshot(
                           event, vectors.loc[event.vector_open_time],
                           snapshot_id=f"{snapshot_id}:{candidate_id}", decision_time=window.decision_time,
                           available_at=available, source=source))
        result["candidates"].append(payload)
    if result["candidates"]:
        result["status"] = "DETECTED_UNPRICED"
    return result

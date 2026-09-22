"""Closed, available-bar EMA observations; not candidate generation or live parity."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import math

import numpy as np
import pandas as pd

from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
from .bars import select_closed_bars
from ._vendor import tr


SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
ADAPTER_VERSION = "chartdesk-closed-ema-v1"


def _time(value):
    return value.isoformat().replace("+00:00", "Z")


def _finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite numerical EMA result after warmup")
    return number


def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
                 history_start, max_age_seconds, session_schedule=None) -> dict:
    """Use all selected dependencies; missing history never shortens an EMA seed.

    The contiguous closed-bar policy is a research adapter constraint, not a new
    live trading gate. Per-EMA 2*n warmup comes from features.draw_trend. delta5
    is its raw slope numerator, NOT its ATR-normalized slope. Inputs require a
    caller-defined historical anchor and freshness limit; no calendar is guessed.
    An explicit session_schedule opts into full-interval calendar selection.
    """
    params = dict(instrument=instrument, timeframe=timeframe,
                  decision_time=decision_time, history_start=history_start,
                  max_age_seconds=max_age_seconds)
    calendar_metadata = {}
    if session_schedule is None:
        window = select_closed_bars(bars, **params)
    else:
        from .session_bars import select_session_bars
        window = select_session_bars(bars, **params, session_schedule=session_schedule)
        calendar_metadata = {"calendar": {
            "calendar_id": session_schedule.calendar_id, "version": session_schedule.version,
            "source": session_schedule.source, "schedule_sha256": window.schedule_sha256,
            "available_at": _time(session_schedule.available_at),
            "coverage_start": _time(session_schedule.coverage_start),
            "coverage_end": _time(session_schedule.coverage_end),
            "expected_bars": window.expected_bars,
            "missing_opens": [_time(t) for t in window.missing_opens],
            "out_of_session_bars": window.out_of_session_bars,
            "straddling_bars": window.straddling_bars,
            "adapter_version": "session-closed-history-v1",
            "execution_truth": False,
        }}
    serialized = asdict(window)
    encoded = json.dumps(serialized, sort_keys=True, separators=(",", ":"),
                         allow_nan=False, default=lambda x: _time(x) if isinstance(x, datetime) else x)
    window_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    source = f"chart-desk@{SOURCE_COMMIT};{ADAPTER_VERSION};window={window_hash}"
    definitions, observations = [], []
    periods = []
    values = {}

    if window.blocker is None:
        frame = pd.DataFrame({"close": [b.close for b in window.bars]},
                             index=pd.DatetimeIndex([b.opened_at for b in window.bars]))
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                averages = tr.emas(frame)
                for n in tr.TR_EMAS:
                    if len(frame) >= 2 * n:
                        current = _finite(averages[f"ema{n}"].iloc[-1])
                        previous = _finite(averages[f"ema{n}"].iloc[-6])
                        values[f"ema{n}"] = current
                        values[f"above_ema{n}"] = bool(frame["close"].iloc[-1] > current)
                        values[f"ema{n}_delta5"] = _finite(current - previous)
                        periods.append(n)
                if periods:
                    ordered = sorted(periods, key=lambda n: -values[f"ema{n}"])
                    values["ema_order"] = ">".join(str(n) for n in ordered)
                    if len(periods) == len(tr.TR_EMAS):
                        values["ema_stacked"] = ordered in (list(tr.TR_EMAS), list(reversed(tr.TR_EMAS)))
                if 50 in periods:
                    cloud = tr.ema_cloud(frame).iloc[-1]
                    for key in ("basis", "upper", "lower", "size"):
                        values[f"cloud50_{key}"] = _finite(cloud[key])
                    close = float(frame["close"].iloc[-1])
                    values["cloud50_location"] = (
                        "ABOVE" if close > values["cloud50_upper"] else
                        "BELOW" if close < values["cloud50_lower"] else "INSIDE"
                    )
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("numeric overflow in pinned EMA calculation") from exc

    fields = []
    for n in tr.TR_EMAS:
        fields.extend([(f"ema{n}", "number", "price"),
                       (f"above_ema{n}", "boolean", "boolean"),
                       (f"ema{n}_delta5", "number", "price_change_over_5_bars")])
    fields += [("ema_order", "category", "descending_period_list"),
               ("ema_stacked", "boolean", "boolean")]
    fields += [(f"cloud50_{k}", "number", "price") for k in ("basis", "upper", "lower", "size")]
    fields.append(("cloud50_location", "category", "relation"))
    for key, dtype, unit in fields:
        feature_id = f"chartdesk.{timeframe}.{key}"
        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
        if key in values:
            status, value = "KNOWN", values[key]
            observed = window.bars[-1].closed_at
            available = max(b.available_at for b in window.bars)
            if session_schedule is not None:
                available = max(available, window.calendar_available_at)
        else:
            status = ("STALE" if window.blocker == "STALE" else
                      "UNAVAILABLE" if window.blocker else "UNKNOWN")
            value = None
            observed = available = window.decision_time
        observations.append(FeatureObservation(feature_id, value, status, observed, available, source))

    result = build_snapshot(snapshot_id, window.decision_time, definitions, observations).to_payload()
    return {**result, **calendar_metadata, "instrument": window.instrument, "timeframe": window.timeframe,
            "window_sha256": window_hash, "window_blocker": window.blocker,
            "history_start": _time(window.history_start), "max_age_seconds": window.max_age_seconds,
            "coverage": {"selected_bars": len(window.bars), "available_ema_periods": periods},
            "calculation": {"source_commit": SOURCE_COMMIT, "adapter_version": ADAPTER_VERSION,
                            "pandas_version": pd.__version__, "numpy_version": np.__version__},
            "ready_for_replay": False, "ready_for_training": False}

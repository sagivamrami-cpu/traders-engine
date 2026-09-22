"""Original session clock with a required explicit decision time."""
from __future__ import annotations
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from .map_sessions import SessionSpec, SESSIONS, _hm


def session_mask(
    index: pd.DatetimeIndex, spec: SessionSpec, *, include_weekends: bool = False
) -> pd.Series:
    """Boolean mask over a UTC index for bars inside `spec`.

    Sessions that wrap midnight local time (Sydney does not, but a custom one
    might) are handled by comparing against minutes-since-local-midnight with a
    wrap-aware test.
    """
    local = index.tz_convert(ZoneInfo(spec.tz))
    minutes = local.hour * 60 + local.minute
    s_h, s_m = _hm(spec.start)
    e_h, e_m = _hm(spec.end)
    start, end = s_h * 60 + s_m, e_h * 60 + e_m
    inside = (minutes >= start) & (minutes < end) if start < end else \
             (minutes >= start) | (minutes < end)
    if not include_weekends:
        inside &= np.isin(local.dayofweek, list(spec.weekdays))
    return pd.Series(inside, index=index)


def current_session_at(*, decision_time: pd.Timestamp, **kw) -> list[str]:
    """Which sessions are open right now (UTC)."""
    ts = pd.Timestamp(decision_time)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    idx = pd.DatetimeIndex([ts])
    return [k for k, spec in SESSIONS.items()
            if bool(session_mask(idx, spec, **kw).iloc[0])]

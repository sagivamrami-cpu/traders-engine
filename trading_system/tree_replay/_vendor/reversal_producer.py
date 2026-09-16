from __future__ import annotations
import pandas as pd
from .level_reversal import Reversal, _utc, LIVE_MAX_AGE_S
from .reversal_pricing import build_plan
from . import pricing as tradeplan


def find_at(symbol: str, *, decision_time, source, map_source, detector):
    """Live read: ``(event, plan)`` for the newest fresh exact-TV setup."""
    basis = source
    levelmap = map_source
    detect_frame = detector
    now = _utc(decision_time)
    levels, level_corr = levelmap.build(symbol)
    if not levels or level_corr is None or getattr(level_corr, "unverified", False):
        return None
    candidates: list[tuple[Reversal, pd.DataFrame]] = []
    for tf in ("5m", "15m"):
        try:
            df, corr = basis.fetch_corrected(symbol, tf, 10)
        except Exception:
            continue
        if corr is None or getattr(corr, "unverified", False) or getattr(corr, "source", "") == "none":
            continue
        found = detect_frame(symbol, tf, df, levels, now=now,
                             max_age_s=LIVE_MAX_AGE_S[tf])
        candidates += [(event, df) for event in found]
    if not candidates:
        return None
    candidates.sort(key=lambda row: (row[0].confirmed_at,
                                     row[0].timeframe == "5m"), reverse=True)
    event, history = candidates[0]
    return event, build_plan(event, levels, history)


def conflicts(reversal: tradeplan.Plan | None,
              candidate: tradeplan.Plan | None) -> bool:
    """A tradeable fresh reversal outranks an opposite producer."""
    return bool(reversal and candidate and reversal.tradeable
                and reversal.symbol == candidate.symbol
                and reversal.direction and candidate.direction
                and reversal.direction != candidate.direction)

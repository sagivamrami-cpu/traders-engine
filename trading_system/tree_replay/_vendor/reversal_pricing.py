"""Pure pinned chart-desk pricing subset; commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9."""

from __future__ import annotations
import pandas as pd
from .level_reversal import Reversal, _normalise
from . import pricing as tradeplan
from . import atr as tr


def build_plan(event: Reversal, levels, history: pd.DataFrame) -> tradeplan.Plan:
    """Price the detected reversal without weakening the desk's R:R rules."""
    frame = _normalise(history)
    frame = frame[frame.index < event.confirmed_at]
    atr = float(tr.atr(frame).iloc[-1]) if len(frame) else 0.0
    atr = atr if atr > 0 else max(abs(event.close - event.level_price), 1e-9)
    entry = float(event.level_price)
    short = event.direction == "שורט"
    warnings: list[str] = []
    raw_stop = (event.sweep_extreme + 0.15 * atr if short
                else event.sweep_extreme - 0.15 * atr)
    style = "scalp" if event.timeframe == "5m" else "intraday"
    stop = tradeplan.apply_stop_band(event.symbol, entry, raw_stop, atr,
                                     warnings, style=style)
    cands = [(x.name, float(x.price)) if hasattr(x, "name")
             else (str(x[0]), float(x[1])) for x in (levels or [])]
    targets, obstacles, refusal = tradeplan.resolve_ladder(
        cands, event.symbol, entry, stop, short, atr)
    vector_he = {"red": "אדום", "violet": "סגול",
                 "green": "ירוק", "blue": "כחול"}.get(
                     event.vector_kind, event.vector_kind)
    reasons = [
        f"רמה: {event.level_name} {entry:,.2f}",
        f"וקטור: PVSRA {vector_he} על {event.timeframe}",
        f"הגעה {event.approach} וסגירה חוזרת דרך הרמה",
        ("טריגר: נר אישור לאחר ספיגה" if event.pattern.startswith("two_bar")
         else "טריגר: נר ספיגה שנסגר בחזרה מעל/מתחת לרמה"),
    ]
    return tradeplan.Plan(
        symbol=event.symbol, close=event.close, kind="reversal",
        direction=event.direction, entry=entry, stop=stop,
        targets=targets, obstacles=obstacles, refusal=refusal,
        reasons=reasons, warnings=warnings, atr=atr, style=style)

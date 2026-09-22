from __future__ import annotations
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SessionSpec:
    name: str
    tz: str
    start: str          # local "HH:MM"
    end: str            # local "HH:MM"
    weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)   # Monday=0, in local time
    note: str = ""


SESSIONS: dict[str, SessionSpec] = {
    "sydney":    SessionSpec("Sydney", "Australia/Sydney", "08:00", "16:00",
                             note="NZX open through ASX close"),
    "tokyo":     SessionSpec("Tokyo", "Asia/Tokyo", "09:00", "15:00"),
    "hongkong":  SessionSpec("Hong Kong", "Asia/Hong_Kong", "09:30", "16:00"),
    "frankfurt": SessionSpec("Frankfurt", "Europe/Berlin", "08:00", "17:30"),
    "london":    SessionSpec("London", "Europe/London", "08:00", "16:30"),
    "eu_brinks": SessionSpec("EU Brinks", "Europe/London", "08:00", "09:00",
                             note="first hour of London"),
    "newyork":   SessionSpec("New York", "America/New_York", "09:30", "16:00"),
    "us_brinks": SessionSpec("US Brinks", "America/New_York", "09:00", "10:00",
                             note="the hour before the NY cash open"),
}


def _hm(s: str) -> tuple[int, int]:
    h, _, m = s.partition(":")
    return int(h), int(m or 0)


def psy_levels(df: pd.DataFrame, mode: str = "crypto") -> dict:
    """Weekly "psychological" high/low: the range of the week's first Asian session.

    The idea is that the thin, low-participation session that opens the trading
    week prints a range which the rest of the week then treats as a reference.

    Two conventions, because the week starts at different moments:

    * ``crypto`` -- Sydney open on **Saturday** through the end of Tokyo, since
      crypto trades the weekend.
    * ``forex`` -- Sydney open on **Sunday** through the end of Tokyo Monday,
      the first session of an FX week.

    Needs intraday bars of 1h or finer; on coarser data the window does not
    resolve and this returns ``available: False`` rather than a wrong number.

    The window definition is a convention, not a law -- reconcile it against the
    chart once before trusting the exact levels.
    """
    if mode not in ("crypto", "forex"):
        raise ValueError("mode must be 'crypto' or 'forex'")
    if len(df) < 2:
        return {"available": False, "reason": "not enough bars"}

    step = df.index.to_series().diff().median()
    if pd.isna(step) or step > pd.Timedelta(hours=1):
        return {"available": False, "reason": "needs 1h bars or finer"}

    syd = SESSIONS["sydney"]
    local = df.index.tz_convert(ZoneInfo(syd.tz))
    # Sydney local Saturday (crypto) or Sunday (forex) 08:00 -> end of Tokyo
    start_dow = 5 if mode == "crypto" else 6
    in_window = (
        (local.dayofweek == start_dow) & (local.hour >= 8)
    ) | (
        (local.dayofweek == (start_dow + 1) % 7) & (local.hour < 17)
    )
    sub = df.loc[np.asarray(in_window)]
    if sub.empty:
        return {"available": False, "reason": f"no {mode} week-open session in sample"}

    # group into distinct weekly windows by gap
    gaps = sub.index.to_series().diff() > pd.Timedelta(hours=12)
    grp = gaps.cumsum()
    last = sub.loc[(grp == grp.iloc[-1]).to_numpy()]
    # THE PLANNED END, not the last bar seen. `end` is last.index[-1] -- on a
    # causal feed that is always <= now, so the tree's "are we still inside
    # the forming window?" check (now < end) could never be True and the
    # provisional-PSY label never fired once. Found by Codex 2026-09-01,
    # confirmed by tree_health: the key was never written on any symbol.
    # window_end is when the window is SCHEDULED to close: 17:00 Sydney on
    # the window's second day.
    last_local = last.index[-1].tz_convert(ZoneInfo(syd.tz))
    end_day = last_local.normalize()
    if last_local.dayofweek == start_dow:      # still on day one
        end_day = end_day + pd.Timedelta(days=1)
    window_end = end_day + pd.Timedelta(hours=17)
    return {
        "available": True, "mode": mode,
        "psy_high": float(last["high"].max()), "psy_low": float(last["low"].min()),
        "start": str(last.index[0]), "end": str(last.index[-1]),
        "window_end": str(window_end.tz_convert("UTC")),
        "bars": int(len(last)),
    }
